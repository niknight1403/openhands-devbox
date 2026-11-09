#!/usr/bin/env python3
"""Free Route Hunter — findet automatisch eine kostenlose, erreichbare LLM-Route.

Der Hunter ersetzt fest verdrahtete Modellnamen. Er baut die Kandidatenliste aus
den tatsächlich hinterlegten Zugangsdaten, sortiert sie nach Eignung für einen
agentischen Coding-Lauf, prüft jeden Kandidaten mit einem echten Mini-Aufruf
(max_tokens=1) und schreibt erst die antwortende Route in die Umgebung.

Eigenschaften
-------------
* Nur freie bzw. freie Kontingent-Routen. Der bezahlte OpenAI-Anbieter wird nur
  genutzt, wenn er ausdrücklich erzwungen oder per Schalter erlaubt wird.
* OpenRouter-Kandidaten werden dynamisch aus ``/models`` gelesen: nur Modelle,
  deren Prompt- und Completion-Preis 0 ist, mit ausreichendem Kontextfenster.
* Zugangsdaten werden niemals ausgegeben, geloggt oder in den Report
  geschrieben. Jeder Schlüssel geht ausschließlich an seinen eigenen Anbieter.
* Ohne erreichbare Route bricht der Aufruf mit klarer Meldung ab, statt einen
  Agenten stillschweigend mit einem toten Modell zu starten.

CLI
---
    python3 scripts/free_route_hunter.py                  # jagen + GITHUB_ENV schreiben
    python3 scripts/free_route_hunter.py --list           # nur Kandidaten zeigen
    python3 scripts/free_route_hunter.py --json           # Report als JSON
    python3 scripts/free_route_hunter.py --report out.json --summary
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

USER_AGENT = "openhands-devbox-free-route-hunter/1.0"
DEFAULT_TIMEOUT = 20.0
DEFAULT_MAX_PER_PROVIDER = 5
DEFAULT_MIN_CONTEXT = 16_000
BATCH_SIZE = 4
ANONYMOUS_KEY = "anonymous"


@dataclass(frozen=True)
class Provider:
    """Ein OpenAI-kompatibler Anbieter mit kostenlosem Kontingent."""

    name: str
    base_url: str
    key_envs: tuple[str, ...]
    models: tuple[str, ...] = ()
    litellm_prefix: str = "openai/"
    priority: int = 50
    discover: bool = False
    needs_key: bool = True
    paid: bool = False
    note: str = ""

    def credential(self, env: dict[str, str]) -> str:
        """Erster gesetzter Schlüssel des Anbieters; leer, wenn keiner gesetzt ist."""
        for name in self.key_envs:
            value = env.get(name, "").strip()
            if value:
                return value
        return ""


#: Alle Anbieter in Standard-Priorität (kleiner = bevorzugt). Jeder Eintrag ist
#: ein kostenloses Kontingent; ``openai`` ist der bezahlte Notnagel.
PROVIDERS: tuple[Provider, ...] = (
    Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        key_envs=("OPENROUTER_API_KEY",),
        litellm_prefix="openrouter/",
        priority=10,
        discover=True,
        note="dynamische Liste aller :free-Modelle inkl. Tool-Unterstützung",
    ),
    Provider(
        name="cerebras",
        base_url="https://api.cerebras.ai/v1",
        key_envs=("CEREBRAS_API_KEY",),
        models=("qwen-3-coder-480b", "qwen-3-235b-a22b-instruct-2507", "gpt-oss-120b"),
        priority=20,
        note="kostenloses Tageskontingent, sehr schnelle Inferenz",
    ),
    Provider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        key_envs=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        models=("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"),
        priority=30,
        note="Google-AI-Studio-Free-Tier",
    ),
    Provider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        key_envs=("GROQ_API_KEY",),
        models=("moonshotai/kimi-k2-instruct", "openai/gpt-oss-120b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"),
        priority=40,
        note="kostenloses Kontingent pro Minute",
    ),
    Provider(
        name="github",
        base_url="https://models.github.ai/inference",
        key_envs=("GH_MODELS_TOKEN", "GITHUB_MODELS_TOKEN"),
        models=("openai/gpt-4o-mini", "mistral-ai/mistral-small-2503", "meta/llama-4-scout-17b-16e-instruct"),
        priority=50,
        note="GitHub Models, kostenloses Kontingent für öffentliche Repositories",
    ),
    Provider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        key_envs=("MISTRAL_API_KEY",),
        models=("mistral-small-latest", "codestral-latest", "open-mistral-nemo"),
        priority=60,
        note="Free-Tier über La Plateforme",
    ),
    Provider(
        name="huggingface",
        base_url="https://router.huggingface.co/v1",
        key_envs=("HF_TOKEN", "HUGGINGFACE_API_KEY"),
        models=(
            "Qwen/Qwen3-Coder-480B-A35B-Instruct:cerebras",
            "openai/gpt-oss-120b:cerebras",
            "Qwen/Qwen3-235B-A22B-Instruct-2507:fireworks-ai",
        ),
        priority=70,
        note="Hugging Face Inference Providers, kostenlose Monatsquote",
    ),
    Provider(
        name="openai",
        base_url="https://api.openai.com/v1",
        key_envs=("OPENAI_API_KEY",),
        models=("gpt-4o-mini", "gpt-4.1-mini"),
        priority=90,
        paid=True,
        note="kostenpflichtig, nur als ausdrücklicher Notnagel",
    ),
    Provider(
        name="pollinations",
        base_url="https://text.pollinations.ai/openai",
        key_envs=(),
        models=("openai",),
        priority=99,
        needs_key=False,
        note="schlüsselfreie Reserve, oft ausgelastet",
    ),
)

PROVIDER_BY_NAME: dict[str, Provider] = {provider.name: provider for provider in PROVIDERS}

#: Signale für Eignung im agentischen Coding-Lauf. Gewicht in Sekunden,
#: negative Werte bevorzugen ein Modell.
CODE_HINTS = ("coder", "code", "qwen3", "qwen2.5-coder", "deepseek", "gpt-oss", "kimi", "devstral", "codestral")
BIG_HINTS = ("ultra", "super", "large", "550b", "480b", "235b", "120b", "70b")
SMALL_HINTS = ("mini", "small", "lite", "tiny", "nano", "micro", "lightning", "flash-lite", "1.7b", "2.6b", "3b", "7b", "8b")
VISION_HINTS = ("vision", "vl", "-vl", "image", "omni")


def _price_is_zero(value: object) -> bool:
    """OpenRouter liefert Preise als String; "0", "0.0" und 0 gelten als gratis."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return float(value) == 0.0
    if isinstance(value, str):
        try:
            return float(value) == 0.0
        except ValueError:
            return False
    return False


@dataclass(frozen=True)
class ModelInfo:
    """Ein einzelnes Kandidatenmodell eines Anbieters."""

    provider: str
    model: str
    context_length: int = 0
    supports_tools: bool = False

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"

    @property
    def display(self) -> str:
        return f"{PROVIDER_BY_NAME[self.provider].litellm_prefix}{self.model}"


def parse_openrouter_free_models(payload: object, min_context: int = DEFAULT_MIN_CONTEXT) -> list[ModelInfo]:
    """Liest alle kostenlosen, ausreichend großen Modelle aus einer OpenRouter-Antwort."""
    if not isinstance(payload, dict):
        return []
    entries = payload.get("data")
    if not isinstance(entries, list):
        return []

    models: list[ModelInfo] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id")
        if not isinstance(model_id, str) or not model_id or model_id in seen:
            continue
        pricing = entry.get("pricing")
        if not isinstance(pricing, dict):
            continue
        free = _price_is_zero(pricing.get("prompt")) and _price_is_zero(pricing.get("completion"))
        if not free and not model_id.endswith(":free"):
            continue
        context = entry.get("context_length")
        context_length = int(context) if isinstance(context, (int, float)) else 0
        if context_length and context_length < min_context:
            continue
        parameters = entry.get("supported_parameters")
        supports_tools = isinstance(parameters, list) and "tools" in parameters
        seen.add(model_id)
        models.append(
            ModelInfo(
                provider="openrouter",
                model=model_id,
                context_length=context_length,
                supports_tools=supports_tools,
            )
        )
    return models


def provider_rank(name: str, prefer: tuple[str, ...] = ()) -> int:
    """Rang des Anbieters: ausdrückliche Wunschreihenfolge vor fester Priorität."""
    if name in prefer:
        return list(prefer).index(name)
    return len(prefer) + PROVIDER_BY_NAME[name].priority


def suitability(info: ModelInfo, prefer: tuple[str, ...] = ()) -> tuple[int, ...] | tuple:
    """Sortierschlüssel: kleiner ist besser. Deterministisch und testbar.

    Reihenfolge der Kriterien: bezahlt zuletzt, Wunsch-/Standardpriorität des
    Anbieters, Tool-Calling (für OpenHands Pflicht), Code-Eignung, Größe,
    Kontextfenster, dann stabiler Name.
    """
    provider = PROVIDER_BY_NAME[info.provider]
    lowered = info.model.lower()

    tool_rank = 0 if info.supports_tools else 1
    code_rank = 0 if any(hint in lowered for hint in CODE_HINTS) else 1
    if any(hint in lowered for hint in SMALL_HINTS):
        size_rank = 2
    elif any(hint in lowered for hint in VISION_HINTS):
        size_rank = 1
    elif any(hint in lowered for hint in BIG_HINTS):
        size_rank = -1
    else:
        size_rank = 0
    # Größerer Kontext ist für agentische Läufe besser; 0 heißt "unbekannt".
    context_rank = 0 if not info.context_length else -min(info.context_length // 32_000, 8)
    paid_rank = 1 if provider.paid else 0
    return (
        paid_rank,
        provider_rank(info.provider, prefer),
        tool_rank,
        code_rank + size_rank,
        context_rank,
        lowered,
    )


def rank_candidates(models: list[ModelInfo], prefer: tuple[str, ...] = ()) -> list[ModelInfo]:
    """Sortiert Kandidaten nach Eignung, ohne Duplikate."""
    seen: set[tuple[str, str]] = set()
    ordered: list[ModelInfo] = []
    for info in sorted(models, key=lambda item: suitability(item, prefer)):
        key = (info.provider, info.model)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(info)
    return ordered


def provider_credential(provider: Provider, env: dict[str, str]) -> str:
    return provider.credential(env)


def available_providers(env: dict[str, str], include_paid: bool = False) -> list[Provider]:
    """Anbieter, die mit den vorhandenen Zugangsdaten tatsächlich nutzbar sind."""
    usable: list[Provider] = []
    for provider in sorted(PROVIDERS, key=lambda item: item.priority):
        if provider.paid and not include_paid:
            continue
        if provider.needs_key and not provider_credential(provider, env):
            continue
        usable.append(provider)
    return usable


def missing_providers(env: dict[str, str]) -> list[str]:
    return [
        provider.name
        for provider in sorted(PROVIDERS, key=lambda item: item.priority)
        if provider.needs_key and not provider.paid and not provider_credential(provider, env)
    ]


def apply_preferences(env: dict[str, str]) -> list[Provider]:
    """Priorität anhand von HUNTER_PREFER überschreiben ("groq,openrouter")."""
    order = [name.strip() for name in env.get("HUNTER_PREFER", "").split(",") if name.strip()]
    if not order:
        return list(PROVIDERS)
    unknown = [name for name in order if name not in PROVIDER_BY_NAME]
    if unknown:
        print(f"Hinweis: unbekannte Anbieter in HUNTER_PREFER ignoriert: {', '.join(unknown)}")
    ranked = [PROVIDER_BY_NAME[name] for name in order if name in PROVIDER_BY_NAME]
    rest = [provider for provider in PROVIDERS if provider.name not in order]
    return ranked + rest


def forced_candidates(model_input: str) -> list[ModelInfo]:
    """Wunschmodell aus der Nutzereingabe. Anbietername voranstellen, wenn bekannt."""
    wanted = model_input.strip()
    if not wanted:
        return []
    # 1. Eindeutiger Anbietername vor dem Schrägstrich ("groq/...", "openai/...").
    for provider in PROVIDERS:
        prefix = f"{provider.name}/"
        if wanted.startswith(prefix):
            return [ModelInfo(provider=provider.name, model=wanted[len(prefix):])]
    # 2. LiteLLM-Präfixe, die sich vom Anbieternamen unterscheiden (z. B. "openrouter/").
    for prefix, provider in unique_litellm_prefixes().items():
        if wanted.startswith(prefix):
            return [ModelInfo(provider=provider.name, model=wanted[len(prefix):])]
    # 3. "qwen/qwen3-coder:free" ohne Anbieterangabe gehört zu OpenRouter.
    return [ModelInfo(provider="openrouter", model=wanted)]


def unique_litellm_prefixes() -> dict[str, Provider]:
    """Litellm-Präfixe, die nur zu genau einem Anbieter passen (eindeutige Zuordnung)."""
    counts: dict[str, int] = {}
    for provider in PROVIDERS:
        counts[provider.litellm_prefix] = counts.get(provider.litellm_prefix, 0) + 1
    mapping: dict[str, Provider] = {}
    for provider in PROVIDERS:
        prefix = provider.litellm_prefix
        if counts[prefix] == 1 and prefix != f"{provider.name}/":
            mapping[prefix] = provider
    return mapping


def fetch_json(url: str, timeout: float, api_key: str = "") -> object:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - Endpunkt stammt aus dem geprueften Routenkatalog (nur https)
        return json.loads(response.read().decode("utf-8"))


def discover_openrouter(timeout: float = DEFAULT_TIMEOUT, env: dict[str, str] | None = None) -> list[ModelInfo]:
    """Holt die freien OpenRouter-Modelle. Fehler werden zu einer leeren Liste."""
    environment = env or {}
    min_context = int(environment.get("HUNTER_MIN_CONTEXT", DEFAULT_MIN_CONTEXT) or DEFAULT_MIN_CONTEXT)
    try:
        payload = fetch_json(f"{PROVIDER_BY_NAME['openrouter'].base_url}/models", timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        print("Warnung: OpenRouter-Modellliste nicht abrufbar; es bleiben die übrigen Anbieter.")
        return []
    return parse_openrouter_free_models(payload, min_context)


@dataclass
class RouteCheck:
    """Ergebnis eines echten Mini-Aufrufs."""

    ok: bool
    status: int | str
    latency_ms: int


def ping_route(provider: Provider, model: str, api_key: str, timeout: float = DEFAULT_TIMEOUT) -> RouteCheck:
    """Echter Mini-Aufruf: nur HTTP 2xx gilt als erreichbare Route."""
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        f"{provider.base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - Endpunkt stammt aus dem geprueften Routenkatalog (nur https)
            response.read(256)
            latency = int((time.perf_counter() - started) * 1000)
            return RouteCheck(200 <= response.status < 300, response.status, latency)
    except urllib.error.HTTPError as error:
        latency = int((time.perf_counter() - started) * 1000)
        return RouteCheck(False, error.code, latency)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        latency = int((time.perf_counter() - started) * 1000)
        return RouteCheck(False, "error", latency)


def build_candidates(
    env: dict[str, str],
    discover=discover_openrouter,
    max_per_provider: int = DEFAULT_MAX_PER_PROVIDER,
    include_paid: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[ModelInfo]:
    """Baut die geordnete Kandidatenliste aus Wunschmodell und vorhandenen Schlüsseln."""
    exclude = excluded_labels(env)
    forced = forced_candidates(env.get("MODEL_INPUT") or env.get("HUNTER_MODEL") or "")
    forced = [info for info in forced if info.label not in exclude and info.model not in exclude]
    if forced:
        # Ausdrücklicher Wunsch schlägt die Jagd: nur diese Route wird geprüft.
        return forced

    prefer = tuple(name.strip() for name in env.get("HUNTER_PREFER", "").split(",") if name.strip())
    candidates: list[ModelInfo] = []
    for provider in apply_preferences(env):
        if provider.paid and not include_paid:
            continue
        if provider.needs_key and not provider_credential(provider, env):
            continue
        if provider.discover:
            models = discover(timeout, env)
        else:
            models = [ModelInfo(provider=provider.name, model=model) for model in provider.models]
        candidates.extend(rank_candidates(models, prefer)[:max_per_provider])

    ordered = rank_candidates(candidates, prefer)
    hints = [
        info
        for info in load_status_hints(env)
        if info.label not in exclude and info.model not in exclude and usable(info, env)
    ]
    hint_keys = {(info.provider, info.model) for info in hints}
    filtered = [
        info
        for info in ordered
        if (info.provider, info.model) not in hint_keys and info.label not in exclude and info.model not in exclude
    ]
    if hints:
        print(f"Autopilot-Hinweise übernommen: {', '.join(info.label for info in hints)}")
    # Hinweise bringen erprobte Modelle in die Jagd, dürfen die Eignung aber nicht
    # überstimmen: sonst rutscht eine schlüsselfreie, streng limitierte Route vor
    # einen echten Anbieter und der Agentenlauf scheitert am Kontingent.
    return rank_candidates(hints + filtered, prefer)


def hunt(
    candidates: list[ModelInfo],
    env: dict[str, str],
    ping=ping_route,
    timeout: float = DEFAULT_TIMEOUT,
    batch_size: int = BATCH_SIZE,
    report: list[dict] | None = None,
) -> tuple[ModelInfo | None, RouteCheck | None]:
    """Prüft Kandidaten in Rang-Reihenfolge, parallel innerhalb einer kleinen Gruppe."""
    checks = report if report is not None else []
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start:start + batch_size]
        with ThreadPoolExecutor(max_workers=min(batch_size, len(batch))) as pool:
            results = list(
                pool.map(
                    lambda info: ping(
                        PROVIDER_BY_NAME[info.provider],
                        info.model,
                        provider_credential(PROVIDER_BY_NAME[info.provider], env),
                        timeout,
                    ),
                    batch,
                )
            )
        for info, result in zip(batch, results, strict=False):
            checks.append(
                {
                    "provider": info.provider,
                    "model": info.model,
                    "ok": result.ok,
                    "status": result.status,
                    "latency_ms": result.latency_ms,
                }
            )
            state = "OK  " if result.ok else "--  "
            print(f"{state}{info.label} (HTTP {result.status}, {result.latency_ms} ms)")
            if result.ok:
                return info, result
    return None, None


def route_env(info: ModelInfo, api_key: str) -> dict[str, str]:
    """Die Umgebungswerte, die OpenHands für diese Route braucht."""
    provider = PROVIDER_BY_NAME[info.provider]
    return {
        "LLM_MODEL": f"{provider.litellm_prefix}{info.model}",
        "LLM_BASE_URL": provider.base_url,
        "LLM_API_KEY": api_key or ANONYMOUS_KEY,
        "LLM_ROUTE_NAME": info.label,
        "LLM_ROUTE_PROVIDER": provider.name,
    }


def write_env(values: dict[str, str], path: str | None, shell: bool = False) -> None:
    """Schreibt die Routenwerte; ``shell=True`` erzeugt eine sourcebare Export-Datei."""
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            if shell:
                handle.write(f"export {key}={shlex.quote(value)}\n")
            else:
                handle.write(f"{key}={value}\n")


def excluded_labels(env: dict[str, str]) -> set[str]:
    """Routen, die in diesem Lauf nicht erneut geprüft werden (z. B. nach HTTP 429)."""
    raw = env.get("HUNTER_EXCLUDE", "")
    return {item.strip() for item in raw.replace(";", ",").split(",") if item.strip()}


def load_status_hints(env: dict[str, str]) -> list[ModelInfo]:
    """Vom Autopilot bestätigte Routen aus dessen Status-JSON, Werkzeugrouten zuerst."""
    path = env.get("HUNTER_STATUS_FILE", "").strip()
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return []
    entries = payload.get("routes") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return []
    ranked: list[tuple[int, ModelInfo]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("chat_ok"):
            continue
        provider = entry.get("provider")
        model = entry.get("model")
        if not isinstance(provider, str) or not isinstance(model, str):
            continue
        if provider not in PROVIDER_BY_NAME:
            continue
        ranked.append(
            (
                0 if entry.get("tools_ok") else 1,
                ModelInfo(provider=provider, model=model, supports_tools=bool(entry.get("tools_ok"))),
            )
        )
    ranked.sort(key=lambda item: item[0])
    return [info for _, info in ranked]


def usable(info: ModelInfo, env: dict[str, str]) -> bool:
    """Route ist mit den vorhandenen Zugangsdaten nutzbar."""
    provider = PROVIDER_BY_NAME[info.provider]
    return not provider.needs_key or bool(provider_credential(provider, env))


def build_report(
    chosen: ModelInfo | None,
    check: RouteCheck | None,
    checks: list[dict],
    env: dict[str, str],
    providers: list[Provider],
) -> dict:
    """Maschinenlesbarer Report. Enthält bewusst keine Zugangsdaten."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chosen": (
            {
                "provider": chosen.provider,
                "model": chosen.model,
                "litellm_model": chosen.display,
                "latency_ms": check.latency_ms if check else None,
            }
            if chosen
            else None
        ),
        "checked": checks,
        "providers_available": [provider.name for provider in providers],
        "providers_missing_key": missing_providers(env),
        "hint": (
            "Weitere kostenlose Routen freischalten: GEMINI_API_KEY, GROQ_API_KEY, "
            "CEREBRAS_API_KEY, MISTRAL_API_KEY oder HF_TOKEN als Repository-Secret hinterlegen."
        ),
    }


def summary_markdown(report: dict) -> str:
    """Kurze Zusammenfassung für die GitHub-Step-Summary."""
    chosen = report.get("chosen")
    checked = report.get("checked") or []
    lines = ["### Free Route Hunter", ""]
    if chosen:
        lines.append(f"- Route: `{chosen['provider']}` / `{chosen['model']}` ({chosen['latency_ms']} ms)")
    else:
        lines.append("- Route: keine erreichbare Gratis-Route")
    lines.append(f"- Geprüfte Kandidaten: {len(checked)}")
    available = report.get("providers_available") or []
    lines.append(f"- Anbieter mit Schlüssel: {', '.join(available) if available else 'keiner'}")
    missing = report.get("providers_missing_key") or []
    if missing:
        lines.append(f"- Ohne Schlüssel: {', '.join(missing)}")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sucht eine erreichbare kostenlose LLM-Route.")
    parser.add_argument("--model", default="", help="Wunschmodell (LiteLLM-ID); überschreibt MODEL_INPUT")
    parser.add_argument("--prefer", default="", help="Anbieter in Wunschreihenfolge, z. B. groq,openrouter")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout je Prüfaufruf in Sekunden")
    parser.add_argument("--max-per-provider", type=int, default=None, help="Kandidaten je Anbieter")
    parser.add_argument("--min-context", type=int, default=None, help="Mindest-Kontextfenster für OpenRouter")
    parser.add_argument("--env-file", default=None, help="Zieldatei (Standard: $GITHUB_ENV)")
    parser.add_argument("--report", default="", help="JSON-Report an diesen Pfad schreiben")
    parser.add_argument("--summary", action="store_true", help="Markdown in $GITHUB_STEP_SUMMARY schreiben")
    parser.add_argument("--json", action="store_true", help="Report zusätzlich auf stdout ausgeben")
    parser.add_argument("--list", action="store_true", help="Nur Kandidaten anzeigen, keine Aufrufe")
    parser.add_argument("--include-paid", action="store_true", help="Bezahlte Anbieter zulassen")
    parser.add_argument("--exclude", default="", help="Routen ausschließen, z. B. groq:llama-3.3-70b-versatile")
    parser.add_argument("--status-file", default="", help="Status-JSON des LLM-Autopilots als Hinweis")
    parser.add_argument("--shell-export", action="store_true", help="Ausgabedatei mit 'export KEY=...' schreiben")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, env: dict[str, str] | None = None, discover=discover_openrouter, ping=ping_route) -> int:
    environment = dict(os.environ if env is None else env)
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.model:
        environment["MODEL_INPUT"] = args.model
    if args.prefer:
        environment["HUNTER_PREFER"] = args.prefer
    if args.min_context is not None:
        environment["HUNTER_MIN_CONTEXT"] = str(args.min_context)
    if args.exclude:
        environment["HUNTER_EXCLUDE"] = args.exclude
    if args.status_file:
        environment["HUNTER_STATUS_FILE"] = args.status_file

    timeout = args.timeout or float(environment.get("HUNTER_TIMEOUT", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    max_per_provider = args.max_per_provider or int(
        environment.get("HUNTER_MAX_PER_PROVIDER", DEFAULT_MAX_PER_PROVIDER) or DEFAULT_MAX_PER_PROVIDER
    )
    include_paid = args.include_paid or environment.get("HUNTER_ALLOW_PAID", "").strip() in {"1", "true", "yes"}

    providers = available_providers(environment, include_paid=include_paid)
    candidates = build_candidates(
        environment,
        discover=discover,
        max_per_provider=max_per_provider,
        include_paid=include_paid,
        timeout=timeout,
    )

    print(
        f"Free Route Hunter: {len(candidates)} Kandidaten aus "
        f"{len(providers)} Anbieter(n) (Timeout {timeout:.0f}s je Prüfung)."
    )
    if not candidates:
        print(
            "::error::Keine Kandidaten. Hinterlegen Sie mindestens ein Secret: "
            "OPENROUTER_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY, "
            "MISTRAL_API_KEY oder HF_TOKEN."
        )
        return 3

    if args.list:
        for info in candidates:
            print(f"  {info.label} → {info.display}")
        return 0

    checks: list[dict] = []
    chosen, check = hunt(candidates, environment, ping=ping, timeout=timeout, report=checks)

    report = build_report(chosen, check, checks, environment, providers)
    report_path = args.report or environment.get("HUNTER_REPORT", "")
    if report_path:
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    if args.summary and environment.get("GITHUB_STEP_SUMMARY"):
        with open(environment["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(summary_markdown(report))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    if not chosen or not check:
        print("::error::Keine Modellroute antwortete. Geprüft wurden:")
        for entry in checks:
            print(f"::error::  {entry['provider']}:{entry['model']} → HTTP {entry['status']}")
        print(
            "::error::Prüfen Sie Gültigkeit und Kontingent der hinterlegten Schlüssel oder setzen Sie "
            "HUNTER_PREFER auf einen bevorzugten Anbieter."
        )
        return 4

    values = route_env(chosen, provider_credential(PROVIDER_BY_NAME[chosen.provider], environment))
    write_env(
        values,
        args.env_file if args.env_file is not None else environment.get("GITHUB_ENV"),
        # nosec B604 - write_env ist eine eigene Funktion, kein Shell-Aufruf
        shell=args.shell_export,
    )
    print(f"::notice::Gratis-Route bereit: {chosen.label} (HTTP {check.status}, {check.latency_ms} ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
