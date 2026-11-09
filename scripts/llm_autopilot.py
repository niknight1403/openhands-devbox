#!/usr/bin/env python3
"""LLM-Autopilot — hält kostenlose Modell- und Werkzeugrouten dauerhaft am Leben.

Der Autopilot läuft geplant (z. B. alle sechs Stunden) und beantwortet drei
Fragen ohne Zutun:

1. **Welche Route antwortet?** Alle Kandidaten aus den hinterlegten Secrets, aus
   ``config/route-catalog.json`` und aus entfernten Katalogen werden mit einem
   echten Mini-Aufruf geprüft.
2. **Kann die Route Werkzeuge?** OpenHands bricht ohne Tool-Calling ab, deshalb
   prüft ein zweiter Aufruf, ob das Modell tatsächlich einen Funktionsaufruf
   liefert. Nur getestete Werkzeugrouten werden als solche ausgewiesen.
3. **Sind die Plugin-Packs benutzbar?** Jeder konfigurierte Skill-Pack wird
   geladen, sein Frontmatter geprüft und nur bei gültiger Struktur
   übernommen (``mode: install``) oder freigegeben (``mode: validate``).

Ergebnis ist ein maschinenlesbarer Status ohne jeden Zugangsdatenwert, den der
Agenten-Workflow als Hinweis lädt und den die Android-App lesen kann.

CLI
---
    python3 scripts/llm_autopilot.py --status llm-route-status.json --summary
    python3 scripts/llm_autopilot.py --json --max-routes 8
    python3 scripts/llm_autopilot.py --install-packs .agents/skills
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import free_route_hunter as hunter
import local_llm_router

USER_AGENT = "openhands-devbox-llm-autopilot/1.0"
DEFAULT_TIMEOUT = 20.0
DEFAULT_MAX_ROUTES = 24
MAX_SKILL_BYTES = 200_000
GITHUB_API = "https://api.github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"

TOOLS_PROBE = [
    {
        "type": "function",
        "function": {
            "name": "route_probe",
            "description": "Prüft, ob die Werkzeugroute des Modells funktioniert.",
            "parameters": {
                "type": "object",
                "properties": {"stadt": {"type": "string", "description": "Stadtname"}},
                "required": ["stadt"],
            },
        },
    }
]

#: Erlaubte Schlüssel eines Katalogeintrags. Alles andere wird ignoriert.
ROUTE_FIELDS = ("name", "base_url", "models", "key_envs", "litellm_prefix")


@dataclass(frozen=True)
class CatalogRoute:
    """Eine OpenAI-kompatible Route, auch von einem unbekannten Anbieter."""

    name: str
    base_url: str
    models: tuple[str, ...]
    key_envs: tuple[str, ...] = ()
    litellm_prefix: str = "openai/"
    origin: str = "catalog"

    def credential(self, env: dict[str, str]) -> str:
        for name in self.key_envs:
            value = env.get(name, "").strip()
            if value:
                return value
        return ""


def parse_catalog(
    payload: object,
    origin: str,
    warnings: list[str] | None = None,
    allow_credentials: bool = True,
) -> list[CatalogRoute]:
    """Liest einen Katalog (``{"routes": [...]}``) und verwirft unbrauchbare Einträge."""
    warnings = warnings if warnings is not None else []
    if not isinstance(payload, dict):
        warnings.append(f"{origin}: kein JSON-Objekt")
        return []
    entries = payload.get("routes")
    if not isinstance(entries, list):
        warnings.append(f"{origin}: Feld 'routes' fehlt oder ist keine Liste")
        return []

    routes: list[CatalogRoute] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            warnings.append(f"{origin}[{index}]: kein Objekt")
            continue
        name = str(entry.get("name", "")).strip()
        base_url = str(entry.get("base_url", "")).strip()
        models = entry.get("models")
        model_ids = tuple(str(model).strip() for model in models if str(model).strip()) if isinstance(models, list) else ()
        if not name or not model_ids:
            warnings.append(f"{origin}[{index}]: name oder models fehlt")
            continue
        parsed_base = urllib.parse.urlsplit(base_url)
        credentials = parsed_base.username is not None or parsed_base.password is not None
        # HTTPS ist Pflicht; HTTP nur für lokale Endpunkte (Ollama, LiteLLM-Proxy),
        # die den Rechner nie verlassen.
        secure = parsed_base.scheme.lower() == "https" or local_llm_router.is_local_endpoint(base_url)
        if not secure or not parsed_base.hostname or credentials:
            warnings.append(
                f"{origin}[{index}] ({name}): base_url muss HTTPS sein "
                "(HTTP nur für lokale Endpunkte) und darf keine Zugangsdaten enthalten"
            )
            continue
        key_envs = entry.get("key_envs")
        key_names = tuple(str(key).strip() for key in key_envs if str(key).strip()) if isinstance(key_envs, list) else ()
        if key_names and not allow_credentials:
            warnings.append(f"{origin}[{index}] ({name}): entfernte Kataloge duerfen keine Secrets anfordern")
            continue
        prefix = str(entry.get("litellm_prefix", "openai/")).strip() or "openai/"
        routes.append(
            CatalogRoute(
                name=name,
                base_url=base_url.rstrip("/"),
                models=model_ids,
                key_envs=key_names,
                litellm_prefix=prefix,
                origin=origin,
            )
        )
    return routes


def load_katalog(path: str, warnings: list[str]) -> list[CatalogRoute]:
    """Liest den lokalen Zusatzkatalog; ein fehlender Katalog ist kein Fehler."""
    file = Path(path)
    if not file.is_file():
        return []
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        warnings.append(f"{path}: nicht lesbar ({type(error).__name__})")
        return []
    return parse_catalog(payload, origin=str(file), warnings=warnings)


def load_remote_kataloge(urls: list[str], fetch_json, timeout: float, warnings: list[str]) -> list[CatalogRoute]:
    """Lädt entfernte Kataloge; ein toter Katalog stoppt den Lauf nicht."""
    routes: list[CatalogRoute] = []
    for url in urls:
        parsed_url = urllib.parse.urlsplit(url)
        unsicher = (
            parsed_url.scheme.lower() != "https"
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
        )
        if unsicher:
            warnings.append(f"{url}: wird ignoriert (nur HTTPS-Kataloge ohne Zugangsdaten erlaubt)")
            continue
        try:
            payload = fetch_json(url, timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            warnings.append(f"{url}: nicht erreichbar")
            continue
        routes.extend(parse_catalog(payload, origin=url, warnings=warnings, allow_credentials=False))
    return routes


def builtin_routes(env: dict[str, str], discover, timeout: float, max_per_provider: int) -> list[CatalogRoute]:
    """Die bekannten Anbieter aus dem Free Route Hunter als Katalogrouten."""
    routes: list[CatalogRoute] = []
    for provider in hunter.PROVIDERS:
        if provider.needs_key and not provider.credential(env):
            continue
        if provider.discover:
            models = tuple(info.model for info in discover(timeout, env)[:max_per_provider])
        else:
            models = provider.models[:max_per_provider]
        if not models:
            continue
        routes.append(
            CatalogRoute(
                name=provider.name,
                base_url=provider.base_url,
                models=models,
                key_envs=provider.key_envs,
                litellm_prefix=provider.litellm_prefix,
                origin="builtin",
            )
        )
    return routes


def build_candidates(
    routes: list[CatalogRoute], env: dict[str, str], max_routes: int
) -> tuple[list[tuple[CatalogRoute, str, str]], list[str]]:
    """Baut die Prüfliste als (Route, Modell, Schlüssel) ohne Duplikate."""
    candidates: list[tuple[CatalogRoute, str, str]] = []
    warnings: list[str] = []
    seen: set[tuple[str, str]] = set()
    for route in routes:
        key = route.credential(env)
        if route.key_envs and not key:
            continue
        for model in route.models:
            identity = (route.base_url, model)
            if identity in seen:
                continue
            seen.add(identity)
            candidates.append((route, model, key))
            if len(candidates) >= max_routes:
                warnings.append(f"Prüfliste bei {max_routes} Routen gekappt")
                return candidates, warnings
    return candidates, warnings


def post_json(url: str, payload: dict, api_key: str, timeout: float) -> tuple[int, object, int]:
    """Ein HTTP-POST, der nie eine Ausnahme nach außen gibt."""
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - Endpunkt stammt aus dem geprueften Routenkatalog (nur https)
            raw = response.read()
            latency = int((time.perf_counter() - started) * 1000)
            try:
                return response.status, json.loads(raw.decode("utf-8")), latency
            except ValueError:
                return response.status, None, latency
    except urllib.error.HTTPError as error:
        return error.code, None, int((time.perf_counter() - started) * 1000)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return 0, None, int((time.perf_counter() - started) * 1000)


def fetch_json(url: str, timeout: float = DEFAULT_TIMEOUT, token: str = "") -> object:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - Endpunkt stammt aus dem geprueften Routenkatalog (nur https)
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, timeout: float = DEFAULT_TIMEOUT, token: str = "") -> str:
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - Skill-URL zeigt auf eine feste, gepruefte Quelle in https
        return response.read(MAX_SKILL_BYTES + 1).decode("utf-8", errors="replace")


def has_tool_call(payload: object) -> bool:
    """Wertet eine Chat-Antwort darauf aus, ob das Modell wirklich ein Werkzeug aufrief."""
    if not isinstance(payload, dict):
        return False
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return False
    first = choices[0]
    if not isinstance(first, dict):
        return False
    if first.get("finish_reason") in {"tool_calls", "function_call"}:
        return True
    message = first.get("message")
    if isinstance(message, dict):
        if message.get("tool_calls"):
            return True
        if message.get("function_call"):
            return True
    return False


def probe_chat(route: CatalogRoute, model: str, api_key: str, timeout: float, post=post_json) -> dict:
    status, payload, latency = post(
        f"{route.base_url}/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
        api_key,
        timeout,
    )
    return {"ok": 200 <= status < 300, "status": status, "latency_ms": latency, "payload": payload}


def probe_tools(route: CatalogRoute, model: str, api_key: str, timeout: float, post=post_json) -> dict:
    status, payload, latency = post(
        f"{route.base_url}/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": "Nutze das Werkzeug route_probe für Berlin."}],
            "tools": TOOLS_PROBE,
            "tool_choice": "auto",
            "max_tokens": 64,
        },
        api_key,
        timeout,
    )
    return {
        "ok": 200 <= status < 300,
        "status": status,
        "latency_ms": latency,
        "tool_calls": has_tool_call(payload),
    }


def probe_all(
    candidates: list[tuple[CatalogRoute, str, str]],
    timeout: float,
    tool_probe: bool = True,
    post=post_json,
    workers: int = 6,
) -> list[dict]:
    """Prüft alle Kandidaten; der Werkzeugtest läuft nur für antwortende Routen."""

    def run(entry: tuple[CatalogRoute, str, str]) -> dict:
        route, model, key = entry
        result = {
            "provider": route.name,
            "base_url": route.base_url,
            "model": model,
            "litellm_model": f"{route.litellm_prefix}{model}",
            "origin": route.origin,
            "chat_ok": False,
            "tools_ok": False,
            "status": 0,
            "latency_ms": 0,
        }
        chat = probe_chat(route, model, key, timeout, post=post)
        result.update(chat_ok=chat["ok"], status=chat["status"], latency_ms=chat["latency_ms"])
        print(f"{'OK  ' if chat['ok'] else '--  '}{route.name}:{model} (HTTP {chat['status']}, {chat['latency_ms']} ms)")
        if chat["ok"] and tool_probe:
            tools = probe_tools(route, model, key, timeout, post=post)
            result["tools_ok"] = bool(tools["ok"] and tools["tool_calls"])
            result["tool_status"] = tools["status"]
            print(f"    Werkzeugroute: {'ja' if result['tools_ok'] else 'nein'} (HTTP {tools['status']})")
        return result

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(run, candidates))


def rank_probes(results: list[dict]) -> list[dict]:
    """Werkzeugrouten zuerst, danach nach Latenz, dann stabil nach Name."""
    return sorted(
        results,
        key=lambda item: (
            0 if item.get("tools_ok") else 1,
            0 if item.get("chat_ok") else 1,
            item.get("latency_ms", 0),
            item["provider"],
            item["model"],
        ),
    )


def check_skill(text: str) -> tuple[bool, str]:
    """Prüft eine SKILL.md: YAML-Frontmatter mit name und description."""
    if len(text) > MAX_SKILL_BYTES:
        return False, "Datei zu groß"
    stripped = text.lstrip("\ufeff \n")
    if not stripped.startswith("---"):
        return False, "kein YAML-Frontmatter"
    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return False, "Frontmatter nicht geschlossen"
    header = parts[1]
    fields = [line.split(":", 1)[0].strip().lower() for line in header.splitlines() if ":" in line]
    missing = [field for field in ("name", "description") if field not in fields]
    if missing:
        return False, f"Frontmatter ohne {', '.join(missing)}"
    return True, "ok"


def parse_packs(payload: object, warnings: list[str] | None = None) -> list[dict]:
    warnings = warnings if warnings is not None else []
    if not isinstance(payload, dict):
        warnings.append("Plugin-Packs: kein JSON-Objekt")
        return []
    entries = payload.get("packs")
    if not isinstance(entries, list):
        warnings.append("Plugin-Packs: Feld 'packs' fehlt")
        return []
    packs: list[dict] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            warnings.append(f"Plugin-Packs[{index}]: kein Objekt")
            continue
        repo = str(entry.get("repo", "")).strip()
        name = str(entry.get("name", "")).strip() or repo
        if repo.count("/") != 1:
            warnings.append(f"Plugin-Packs[{index}]: repo muss 'owner/name' sein")
            continue
        mode = str(entry.get("mode", "validate")).strip().lower()
        if mode not in {"validate", "install"}:
            warnings.append(f"Plugin-Packs[{index}] ({name}): unbekannter Modus '{mode}', nutze validate")
            mode = "validate"
        select = entry.get("select")
        packs.append(
            {
                "name": name,
                "repo": repo,
                "ref": str(entry.get("ref", "main")).strip() or "main",
                "path": str(entry.get("path", ".agents/skills")).strip().strip("/") or ".agents/skills",
                "mode": mode,
                "select": [str(item).strip() for item in select if str(item).strip()] if isinstance(select, list) else [],
            }
        )
    return packs


def process_pack(
    pack: dict,
    fetch_json_fn=fetch_json,
    fetch_text_fn=fetch_text,
    token: str = "",
    timeout: float = DEFAULT_TIMEOUT,
    install_dir: str | None = None,
) -> dict:
    """Prüft einen Skill-Pack und installiert ihn im Modus ``install``."""
    report = {"name": pack["name"], "repo": pack["repo"], "mode": pack["mode"], "ok": False, "skills": [], "reason": ""}
    listing_url = f"{GITHUB_API}/repos/{pack['repo']}/contents/{pack['path']}?ref={pack['ref']}"
    try:
        listing = fetch_json_fn(listing_url, timeout, token)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        report["reason"] = "Verzeichnis nicht abrufbar"
        return report
    if not isinstance(listing, list):
        report["reason"] = "unerwartete Antwort der Verzeichnisliste"
        return report

    directories = [str(entry.get("name")) for entry in listing if isinstance(entry, dict) and entry.get("type") == "dir"]
    wanted = [name for name in directories if not pack["select"] or name in pack["select"]]
    if not wanted:
        report["reason"] = "keine passenden Skill-Verzeichnisse"
        return report

    installed = 0
    for skill in wanted:
        raw_url = f"{RAW_GITHUB}/{pack['repo']}/{pack['ref']}/{pack['path']}/{skill}/SKILL.md"
        try:
            text = fetch_text_fn(raw_url, timeout, token)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            report["skills"].append({"name": skill, "ok": False, "reason": "SKILL.md nicht abrufbar"})
            continue
        valid, reason = check_skill(text)
        report["skills"].append({"name": skill, "ok": valid, "reason": reason})
        if valid and pack["mode"] == "install" and install_dir:
            target = Path(install_dir) / skill
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text(text, encoding="utf-8")
            installed += 1

    valid_skills = [skill for skill in report["skills"] if skill["ok"]]
    report["ok"] = bool(valid_skills)
    report["installed"] = installed
    if not report["ok"]:
        report["reason"] = "kein gültiger Skill"
    elif pack["mode"] == "validate":
        report["reason"] = "geprüft, nicht kopiert (mode=validate)"
    else:
        report["reason"] = f"{installed} Skill(s) kopiert"
    return report


def load_packs(path: str, warnings: list[str]) -> list[dict]:
    file = Path(path)
    if not file.is_file():
        return []
    try:
        return parse_packs(json.loads(file.read_text(encoding="utf-8")), warnings)
    except (OSError, ValueError):
        warnings.append(f"{path}: nicht lesbar")
        return []


def summary_markdown(status: dict) -> str:
    lines = ["### LLM-Autopilot", ""]
    best = status.get("best")
    if best:
        lines.append(f"- Beste Route: `{best['provider']} / {best['model']}` ({best['latency_ms']} ms)")
        lines.append(f"- Werkzeugroute: {'getestet' if best.get('tools_ok') else 'nicht bestätigt'}")
    else:
        lines.append("- Beste Route: keine erreichbare Gratis-Route")
    reachable = [route for route in status.get("routes", []) if route.get("chat_ok")]
    tool_ready = [route for route in reachable if route.get("tools_ok")]
    lines.append(f"- Antwortende Routen: {len(reachable)} von {len(status.get('routes', []))}")
    lines.append(f"- Davon mit Werkzeugaufruf: {len(tool_ready)}")
    packs = status.get("packs") or []
    if packs:
        for pack in packs:
            lines.append(f"- Plugin-Pack `{pack['name']}`: {'ok' if pack['ok'] else 'nicht nutzbar'} ({pack.get('reason', '')})")
    for warning in status.get("warnings", [])[:6]:
        lines.append(f"- Hinweis: {warning}")
    return "\n".join(lines) + "\n"


def run(
    env: dict[str, str],
    post=post_json,
    fetch_json_fn=fetch_json,
    fetch_text_fn=fetch_text,
    install_dir: str | None = None,
    packs_only: bool = False,
) -> dict:
    started = time.perf_counter()
    warnings: list[str] = []
    timeout = float(env.get("AUTOPILOT_TIMEOUT", DEFAULT_TIMEOUT) or DEFAULT_TIMEOUT)
    token = env.get("GITHUB_TOKEN", "").strip()
    catalog_path = env.get("AUTOPILOT_CATALOG", "config/route-catalog.json")
    pack_path = env.get("AUTOPILOT_PACKS", "config/plugin-packs.json")

    packs = load_packs(pack_path, warnings)
    pack_reports = [process_pack(pack, fetch_json_fn, fetch_text_fn, token, timeout, install_dir) for pack in packs]

    status: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "local" if local_llm_router.offline_requested(env) else "cloud",
        "packs": pack_reports,
        "routes": [],
        "best": None,
        "warnings": warnings,
    }

    if packs_only:
        status["duration_s"] = round(time.perf_counter() - started, 1)
        return status

    max_per_provider = int(env.get("AUTOPILOT_MAX_PER_PROVIDER", 5) or 5)
    max_routes = int(env.get("AUTOPILOT_MAX_ROUTES", DEFAULT_MAX_ROUTES) or DEFAULT_MAX_ROUTES)
    tool_probe = env.get("AUTOPILOT_TOOL_PROBE", "1").strip() not in {"0", "false", "no"}

    offline = local_llm_router.offline_requested(env)
    if offline:
        # Offline-Modus: nur lokale Katalogeinträge. Cloud-Anbieter und entfernte
        # Kataloge werden gar nicht erst geladen, damit kein Prüfaufruf dorthin geht.
        routes = [
            route for route in load_katalog(catalog_path, warnings) if local_llm_router.is_local_endpoint(route.base_url)
        ]
        if not routes:
            warnings.append(
                f"Offline-Modus (LLM_OFFLINE=1), aber kein lokaler Eintrag in {catalog_path}; "
                "prüfe config/local-llm.env und config/route-catalog.json."
            )
        print("Autopilot: Offline-Modus, ausschließlich lokale Routen.")
    else:
        routes = builtin_routes(env, hunter.discover_openrouter, timeout, max_per_provider)
        routes += load_katalog(catalog_path, warnings)
        urls = [url.strip() for url in env.get("AUTOPILOT_CATALOG_URLS", "").split(",") if url.strip()]
        routes += load_remote_kataloge(urls, fetch_json_fn, timeout, warnings)

    candidates, caps = build_candidates(routes, env, max_routes)
    warnings.extend(caps)
    print(f"Autopilot: {len(candidates)} Routenkandidaten aus {len(routes)} Quellen, Werkzeugtest={'an' if tool_probe else 'aus'}.")

    probes = probe_all(candidates, timeout, tool_probe=tool_probe, post=post)
    ranked = rank_probes(probes)
    status["routes"] = ranked
    reachable = [route for route in ranked if route["chat_ok"]]
    status["best"] = reachable[0] if reachable else None
    status["duration_s"] = round(time.perf_counter() - started, 1)
    return status


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hält kostenlose LLM- und Werkzeugrouten aktuell.")
    parser.add_argument("--status", default="", help="Status-JSON an diesen Pfad schreiben")
    parser.add_argument("--summary", action="store_true", help="Markdown in $GITHUB_STEP_SUMMARY schreiben")
    parser.add_argument("--json", action="store_true", help="Status auf stdout ausgeben")
    parser.add_argument("--max-routes", type=int, default=None, help="Obergrenze der Prüfungen")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout je Aufruf in Sekunden")
    parser.add_argument("--no-tool-probe", action="store_true", help="Werkzeugtest überspringen")
    parser.add_argument("--catalog", default="", help="Pfad des lokalen Routen-Katalogs")
    parser.add_argument("--install-packs", default="", help="Zielverzeichnis; kopiert Packs mit mode=install")
    parser.add_argument("--packs-only", action="store_true", help="Nur Plugin-Packs prüfen, keine Modellrouten")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, env: dict[str, str] | None = None, **injected) -> int:
    environment = dict(os.environ if env is None else env)
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.max_routes:
        environment["AUTOPILOT_MAX_ROUTES"] = str(args.max_routes)
    if args.timeout:
        environment["AUTOPILOT_TIMEOUT"] = str(args.timeout)
    if args.no_tool_probe:
        environment["AUTOPILOT_TOOL_PROBE"] = "0"
    if args.catalog:
        environment["AUTOPILOT_CATALOG"] = args.catalog

    status = run(
        environment,
        install_dir=args.install_packs or None,
        packs_only=args.packs_only or bool(args.install_packs),
        **injected,
    )

    status_path = args.status or environment.get("AUTOPILOT_STATUS", "")
    if status_path:
        Path(status_path).write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.summary and environment.get("GITHUB_STEP_SUMMARY"):
        with open(environment["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(summary_markdown(status))
    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))

    if not status["routes"] and not status["packs"]:
        print("::error::Autopilot hatte weder Routen noch Pakete zum Prüfen.")
        return 6
    if status["routes"] and not status["best"]:
        print("::error::Keine Modellroute antwortete. Geprüft wurden:")
        for route in status["routes"]:
            print(f"::error::  {route['provider']}:{route['model']} → HTTP {route['status']}")
        return 5
    best = status["best"]
    if best:
        print(
            f"::notice::Autopilot bereit: {best['provider']}:{best['model']} "
            f"(HTTP {best['status']}, {best['latency_ms']} ms, Werkzeuge={'ja' if best['tools_ok'] else 'nein'})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
