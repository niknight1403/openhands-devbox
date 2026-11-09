#!/usr/bin/env python3
"""Lokale Offline-Route — bindet alle Agentenaufrufe an einen eigenen LLM-Endpunkt.

``config/local-llm.env`` beschreibt den Endpunkt (Ollama, LiteLLM-Proxy oder ein
anderer OpenAI-kompatibler Router). Dieses Skript liest die Werte, prüft sie
gegen die erlaubten lokalen Adressen und schreibt daraus genau die Variablen,
die Agent Canvas für jede Completion, jeden Werkzeugaufruf und jede
Ersatzschleife verwendet::

    LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, LLM_ROUTE_NAME, LLM_ROUTE_PROVIDER,
    LLM_OFFLINE

Im Offline-Modus (``LLM_OFFLINE=1``, Standard aus der Konfigurationsdatei) jagt
weder der Free Route Hunter noch der LLM-Autopilot Cloud-Anbieter. Ein nicht
erreichbarer lokaler Endpunkt wird gemeldet, nicht stillschweigend durch einen
Cloud-Anbieter ersetzt.

CLI
---
    python3 scripts/local_llm_router.py --apply --env-file .env   # Route eintragen
    python3 scripts/local_llm_router.py --check --json            # Endpunkt prüfen
    python3 scripts/local_llm_router.py --print-env               # Werte anzeigen
"""
from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "openhands-devbox-local-router/1.0"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "local-llm.env"
OFFLINE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_TIMEOUT = 20.0

#: Variablen, die Agent Canvas für die Route liest. ``--apply`` ersetzt genau diese.
ROUTE_KEYS = (
    "LLM_OFFLINE",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "LLM_ROUTE_NAME",
    "LLM_ROUTE_PROVIDER",
)

#: Sinnvolle Vorgaben, falls die Konfigurationsdatei fehlt.
DEFAULTS: dict[str, str] = {
    "LLM_OFFLINE": "1",
    "LOCAL_LLM_STRICT": "1",
    "LOCAL_LLM_BASE_URL": "http://host.docker.internal:11434/v1",
    "LOCAL_LLM_MODEL": "qwen2.5-coder:7b",
    "LOCAL_LLM_LITELLM_PREFIX": "openai/",
    "LOCAL_LLM_API_KEY": "local-dummy-key",
    "LOCAL_LLM_TIMEOUT": "20",
}

#: Namen lokaler Hosts, die kein Namensdienst auflösen muss.
LOCAL_HOSTS = frozenset(
    {
        "localhost",
        "host.docker.internal",
        "gateway.docker.internal",
        "host.containers.internal",
    }
)


@dataclass(frozen=True)
class LocalRoute:
    """Die aufgelöste lokale Route in der Form, die Agent Canvas erwartet."""

    base_url: str
    model: str
    litellm_prefix: str = "openai/"
    api_key: str = "local-dummy-key"
    offline: bool = True
    strict: bool = True
    timeout: float = DEFAULT_TIMEOUT

    @property
    def model_string(self) -> str:
        """Modell-ID mit LiteLLM-Präfix, wie in ``LLM_MODEL`` erwartet."""
        return f"{self.litellm_prefix}{self.model}" if self.litellm_prefix else self.model

    @property
    def label(self) -> str:
        return f"local:{self.model}"

    def masked_key(self) -> str:
        if not self.api_key:
            return ""
        return f"{self.api_key[:4]}***" if len(self.api_key) > 4 else "***"


@dataclass(frozen=True)
class HttpResult:
    """Antwort eines Prüfaufrufs; Fehler werden zu Werten, nicht zu Ausnahmen."""

    status: int | str
    payload: object | None = None
    error: str = ""


@dataclass(frozen=True)
class ProbeResult:
    """Ergebnis der echten Prüfung eines lokalen Endpunkts."""

    models_ok: bool = False
    model_listed: bool = False
    chat_ok: bool = False
    tools_ok: bool = False
    latency_ms: int = 0
    status: int | str = "error"
    error: str = ""

    @property
    def ok(self) -> bool:
        """Für den Agentenlauf zählt die echte Chat-Antwort."""
        return self.chat_ok

    def as_dict(self) -> dict:
        return {
            "models_ok": self.models_ok,
            "model_listed": self.model_listed,
            "chat_ok": self.chat_ok,
            "tools_ok": self.tools_ok,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "error": self.error,
        }


def offline_requested(env: dict[str, str]) -> bool:
    """Ist der Offline-Modus aktiv? Nur ``LLM_OFFLINE`` entscheidet, nicht die Datei."""
    return str(env.get("LLM_OFFLINE", "")).strip().lower() in OFFLINE_VALUES


def is_local_host(host: str | None) -> bool:
    """Lokale Adresse? Loopback, privates Netz oder ein Docker-/LAN-Name."""
    if not host:
        return False
    name = host.strip().strip("[]").lower()
    if name in LOCAL_HOSTS:
        return True
    if name.endswith(".localhost") or name.endswith(".local") or name.endswith(".internal"):
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local or address.is_unspecified


def is_local_endpoint(url: str) -> bool:
    """Darf dieser Endpunkt als lokale Route gelten? HTTP ist nur lokal erlaubt."""
    try:
        parsed = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return False
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    return is_local_host(parsed.hostname)


def read_env_file(path: str | os.PathLike[str] | None) -> dict[str, str]:
    """Liest ``KEY=WERT``-Zeilen; Kommentare und Leerzeilen werden übersprungen."""
    if not path:
        return {}
    file = Path(path)
    if not file.is_file():
        return {}
    values: dict[str, str] = {}
    try:
        lines = file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = cleaned[1:-1]
        values[key] = cleaned
    return values


def _number(value: str, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def load_config(env: dict[str, str] | None = None, config_path: str | os.PathLike[str] | None = None) -> LocalRoute:
    """Vorgaben < ``config/local-llm.env`` < Umgebungsvariablen.

    Die Umgebung gewinnt, damit ein Lauf ohne Dateiänderung umgelenkt werden kann.
    """
    environment = env if env is not None else os.environ
    path = config_path or environment.get("LOCAL_LLM_CONFIG") or DEFAULT_CONFIG
    merged = dict(DEFAULTS)
    merged.update(read_env_file(path))
    for key in DEFAULTS:
        if key == "LOCAL_LLM_LITELLM_PREFIX":
            # Ein bewusst leerer Wert schaltet das Präfix ab (nackte Modell-ID).
            if "LOCAL_LLM_LITELLM_PREFIX" in environment:
                merged[key] = str(environment["LOCAL_LLM_LITELLM_PREFIX"]).strip()
            continue
        value = str(environment.get(key, "")).strip()
        if value:
            merged[key] = value
    base_url = merged["LOCAL_LLM_BASE_URL"].strip().rstrip("/")
    prefix = merged["LOCAL_LLM_LITELLM_PREFIX"].strip()
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return LocalRoute(
        base_url=base_url,
        model=merged["LOCAL_LLM_MODEL"].strip(),
        litellm_prefix=prefix,
        api_key=merged["LOCAL_LLM_API_KEY"].strip(),
        offline=offline_requested(merged),
        strict=merged["LOCAL_LLM_STRICT"].strip().lower() in OFFLINE_VALUES,
        timeout=_number(merged["LOCAL_LLM_TIMEOUT"], DEFAULT_TIMEOUT),
    )


def validate(route: LocalRoute) -> None:
    """Harte Sperre: im strikten Modus ist nur ein lokaler Endpunkt zulässig."""
    if not route.base_url:
        raise ValueError("LOCAL_LLM_BASE_URL fehlt; ohne Endpunkt startet kein Agentenlauf.")
    if not route.model:
        raise ValueError("LOCAL_LLM_MODEL fehlt; ohne Modell-ID startet kein Agentenlauf.")
    if route.strict and not is_local_endpoint(route.base_url):
        raise ValueError(
            f"LOCAL_LLM_BASE_URL '{route.base_url}' ist nicht lokal. "
            "Im strikten Modus (LOCAL_LLM_STRICT=1) sind nur Loopback-, private "
            "und Docker-Host-Adressen erlaubt. Für einen bewusst entfernten "
            "Router LOCAL_LLM_STRICT=0 setzen."
        )


def route_values(route: LocalRoute) -> dict[str, str]:
    """Die Laufzeitwerte, die Agent Canvas in der ``.env`` liest."""
    return {
        "LLM_OFFLINE": "1" if route.offline else "0",
        "LLM_MODEL": route.model_string,
        "LLM_BASE_URL": route.base_url,
        "LLM_API_KEY": route.api_key,
        "LLM_ROUTE_NAME": route.label,
        "LLM_ROUTE_PROVIDER": "local",
    }


def shell_export(route: LocalRoute, show_key: bool = False) -> list[str]:
    """Sourcebare Export-Zeilen, ohne den Schlüssel zu zeigen."""
    lines = []
    for key, value in route_values(route).items():
        if key == "LLM_API_KEY" and not show_key:
            value = route.masked_key()
        lines.append(f"export {key}={value}")
    return lines


def write_route_env(path: str | os.PathLike[str], route: LocalRoute) -> dict[str, str]:
    """Schreibt die Routenwerte in die Zieldatei und entfernt alte Routenzeilen.

    Idempotent: wiederholte Läufe erzeugen keine doppelten Einträge, andere
    Zeilen (etwa ``LOCAL_BACKEND_API_KEY``) bleiben unverändert.
    """
    file = Path(path)
    existing: list[str] = []
    if file.is_file():
        existing = file.read_text(encoding="utf-8").splitlines()
    kept = [
        line
        for line in existing
        if not (line.split("=", 1)[0].strip() in ROUTE_KEYS or line.split("=", 1)[0].strip().startswith("export LLM_"))
    ]
    values = route_values(route)
    kept.extend(f"{key}={value}" for key, value in values.items())
    file.write_text("\n".join(kept) + "\n", encoding="utf-8")
    with contextlib.suppress(OSError):
        # Nur auf exotischen Dateisystemen ohne Rechte-Modell nicht moeglich.
        os.chmod(file, 0o600)
    return values


def _decode(body: bytes) -> object | None:
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return None


def http_json(
    method: str,
    url: str,
    payload: dict | None = None,
    api_key: str = "",
    timeout: float = DEFAULT_TIMEOUT,
) -> HttpResult:
    """Ein JSON-Aufruf gegen den lokalen Endpunkt; Fehler werden zu Werten."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - Ziel ist der lokal konfigurierte Endpunkt
            return HttpResult(response.status, _decode(response.read(2_000_000)))
    except urllib.error.HTTPError as error:
        return HttpResult(error.code, None, f"HTTP {error.code}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return HttpResult("error", None, type(error).__name__)


def list_models(route: LocalRoute, call=http_json, timeout: float | None = None) -> tuple[bool, list[str]]:
    """Modellliste des Endpunkts; leer, wenn er nicht antwortet."""
    result = call("GET", f"{route.base_url}/models", None, route.api_key, timeout or route.timeout)
    if not (isinstance(result.status, int) and 200 <= result.status < 300):
        return False, []
    payload = result.payload
    entries = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return True, []
    models: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            models.append(entry["id"])
    return True, models


TOOL_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Listet Dateien in einem Verzeichnis.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Verzeichnis"}},
                "required": ["path"],
            },
        },
    }
]


def check_route(
    route: LocalRoute,
    call=http_json,
    timeout: float | None = None,
    probe_tools: bool = True,
) -> ProbeResult:
    """Prüft echte Antworten: Modellliste, Chat-Completion und Werkzeugaufruf."""
    effective = timeout or route.timeout
    models_ok, models = list_models(route, call=call, timeout=effective)
    bare = route.model
    listed = models_ok and any(entry.split(":")[0] == bare.split(":")[0] for entry in models)

    started = time.perf_counter()
    chat = call(
        "POST",
        f"{route.base_url}/chat/completions",
        {"model": bare, "messages": [{"role": "user", "content": "Antworte mit dem Wort OK."}], "max_tokens": 16},
        route.api_key,
        effective,
    )
    latency = int((time.perf_counter() - started) * 1000)
    chat_ok = isinstance(chat.status, int) and 200 <= chat.status < 300
    error = "" if chat_ok else str(chat.error or chat.status)

    tools_ok = False
    if chat_ok and probe_tools:
        tool_call = call(
            "POST",
            f"{route.base_url}/chat/completions",
            {
                "model": bare,
                "messages": [{"role": "user", "content": "Liste die Dateien im Verzeichnis . mit dem Werkzeug."}],
                "tools": TOOL_SPEC,
                "tool_choice": "auto",
                "max_tokens": 256,
            },
            route.api_key,
            effective,
        )
        if isinstance(tool_call.status, int) and 200 <= tool_call.status < 300 and isinstance(tool_call.payload, dict):
            choices = tool_call.payload.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message") if isinstance(choices[0], dict) else None
                tools_ok = bool(isinstance(message, dict) and message.get("tool_calls"))

    return ProbeResult(
        models_ok=models_ok,
        model_listed=listed,
        chat_ok=chat_ok,
        tools_ok=tools_ok,
        latency_ms=latency,
        status=chat.status,
        error=error,
    )


def summary_line(route: LocalRoute, probe: ProbeResult | None = None) -> str:
    """Kurze, kopierbare Beschreibung der aktiven Route."""
    parts = [
        f"Route: {route.label}",
        f"Basis-URL: {route.base_url}",
        f"LLM_MODEL: {route.model_string}",
        f"Modus: {'offline (nur lokal)' if route.offline else 'cloud erlaubt'}",
    ]
    if probe is not None:
        parts.append(
            "Prüfung: "
            + ", ".join(
                [
                    f"Modellliste {'ok' if probe.models_ok else 'nein'}",
                    f"Modell {'gelistet' if probe.model_listed else 'unbekannt'}",
                    f"Chat {'ok' if probe.chat_ok else 'fehlgeschlagen'}",
                    f"Werkzeuge {'ok' if probe.tools_ok else 'nein'}",
                    f"{probe.latency_ms} ms",
                ]
            )
        )
    return " | ".join(parts)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Setzt und prüft die lokale Offline-LLM-Route.")
    parser.add_argument("--config", default="", help="Pfad der Routenkonfiguration (Standard: config/local-llm.env)")
    parser.add_argument("--env-file", default=".env", help="Zieldatei für --apply (Standard: .env)")
    parser.add_argument("--apply", action="store_true", help="Routenwerte in die Zieldatei schreiben")
    parser.add_argument("--check", action="store_true", help="Endpunkt wirklich prüfen (Modellliste, Chat, Werkzeuge)")
    parser.add_argument("--print-env", action="store_true", help="Sourcebare Export-Zeilen ausgeben")
    parser.add_argument("--json", action="store_true", help="Ergebnis als JSON ausgeben")
    parser.add_argument("--show-key", action="store_true", help="Schlüssel im Klartext ausgeben (nur für lokale Dummy-Schlüssel)")
    parser.add_argument("--no-tools", action="store_true", help="Werkzeugprüfung überspringen")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout je Prüfaufruf in Sekunden")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, env: dict[str, str] | None = None, call=http_json) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    environment = dict(os.environ if env is None else env)
    route = load_config(environment, config_path=args.config or None)
    timeout = args.timeout or route.timeout

    try:
        validate(route)
    except ValueError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 7

    if args.print_env:
        for line in shell_export(route, show_key=args.show_key):
            print(line)
        return 0

    probe = check_route(route, call=call, timeout=timeout, probe_tools=not args.no_tools) if args.check else None

    if args.apply:
        if not route.offline:
            # Cloud-Jagd bleibt aktiv; die Datei bleibt unangetastet.
            print("cloud")
            print(
                "Offline-Modus ist aus (LLM_OFFLINE=0): die lokale Route wird nicht erzwungen.",
                file=sys.stderr,
            )
            return 0
        write_route_env(args.env_file, route)
        print("local")
        print(summary_line(route, probe), file=sys.stderr)
        if probe is not None and not probe.ok:
            acknowledge_unreachable(route, probe)  # type: ignore[arg-type]
            if environment.get("LOCAL_LLM_REQUIRE", "").strip().lower() in OFFLINE_VALUES:
                return 5
        return 0

    if args.json:
        payload = {
            "route": {**route_values(route), "LLM_API_KEY": route.masked_key()},
            "mode": "local" if route.offline else "cloud",
        }
        if probe is not None:
            payload["probe"] = probe.as_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if (probe is None or probe.ok) else 5

    print(summary_line(route, probe))
    if probe is not None and not probe.ok:
        acknowledge_unreachable(route, probe)  # type: ignore[arg-type]
        return 5
    return 0


def acknowledge_unreachable(route: LocalRoute, probe: ProbeResult) -> None:
    """Klare Meldung statt stillem Cloud-Fallback."""
    print(
        f"::error::Lokale Route {route.base_url} antwortet nicht ({probe.error or probe.status}). "
        "Kein Cloud-Fallback: Router starten (z. B. ollama serve) und Modell laden "
        f"('ollama pull {route.model}'), dann erneut prüfen.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    sys.exit(main())
