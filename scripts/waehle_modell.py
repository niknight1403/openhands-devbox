#!/usr/bin/env python3
"""Wählt eine erreichbare Modellroute für den OpenHands-Lauf.

Das Skript prüft jede Kandidatenroute mit einem echten Mini-Aufruf (max_tokens=1)
und schreibt erst die funktionierende Route als LLM_MODEL, LLM_BASE_URL und
LLM_API_KEY nach $GITHUB_ENV. Schlägt alles fehl, bricht der Lauf mit klarer
Meldung ab, statt einen Agenten ohne Modell zu starten.

Zugangsdaten werden nie ausgegeben.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
POLLINATIONS_BASE_URL = "https://text.pollinations.ai/openai"


def free_models(payload: object) -> list[str]:
    """Liefert alle kostenlosen Modell-IDs aus einer OpenRouter-Modellliste."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    ids: list[str] = []
    for entry in data:
        if isinstance(entry, dict):
            model_id = entry.get("id")
            if isinstance(model_id, str) and model_id.endswith(":free"):
                ids.append(model_id)
    return ids


def rank(model_ids: list[str], hints: tuple[str, ...] = ("coder", "code")) -> list[str]:
    """Sortiert Kandidaten: Code-Modelle zuerst, danach stabil nach Länge und Name."""
    def key(model_id: str) -> tuple[int, int, str]:
        lowered = model_id.lower()
        code_bonus = 0 if any(hint in lowered for hint in hints) else 1
        return (code_bonus, len(model_id), model_id)

    seen: set[str] = set()
    ordered: list[str] = []
    for model_id in sorted(model_ids, key=key):
        if model_id not in seen:
            seen.add(model_id)
            ordered.append(model_id)
    return ordered


def normalise(model_id: str) -> str:
    """Entfernt ein eventuell vorhandenes openrouter-Präfix für die Kandidatenliste."""
    return model_id[len("openrouter/"):] if model_id.startswith("openrouter/") else model_id


def ping(base_url: str, model: str, api_key: str, timeout: float = 25.0) -> bool:
    """Echter Mini-Aufruf: nur HTTP 2xx gilt als erreichbare Route."""
    payload = json.dumps(
        {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'anonymous'}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return False


def fetch_free_models(timeout: float = 25.0) -> list[str]:
    try:
        with urllib.request.urlopen(OPENROUTER_MODELS_URL, timeout=timeout) as response:
            return free_models(json.loads(response.read().decode("utf-8")))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return []


def build_routes(env: dict[str, str], free: list[str]) -> list[tuple[str, str, str, str]]:
    """Baut die Kaskade als (Anzeigename, Modell, Basis-URL, Schlüssel)."""
    routes: list[tuple[str, str, str, str]] = []
    wanted = normalise(env.get("MODEL_INPUT", "").strip())

    openrouter_key = env.get("OPENROUTER_API_KEY", "").strip()
    if openrouter_key:
        candidates = [wanted] if wanted else rank(free)
        for model in candidates:
            routes.append((f"openrouter:{model}", model, OPENROUTER_BASE_URL, openrouter_key))

    openai_key = env.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        candidates = [wanted] if wanted else ["gpt-4o-mini"]
        for model in candidates:
            routes.append((f"openai:{model}", model, OPENAI_BASE_URL, openai_key))

    # Letzte Reserve: keyfreie Route, damit ein Lauf ohne Guthaben nicht grundlos scheitert.
    routes.append(("pollinations:openai", "openai", POLLINATIONS_BASE_URL, "anonymous"))

    return routes


def write_env(path: str | None, chosen_model: str, base_url: str, api_key: str) -> None:
    lines = [
        f"LLM_MODEL={chosen_model}",
        f"LLM_BASE_URL={base_url}",
        f"LLM_API_KEY={api_key}",
    ]
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None, env: dict[str, str] | None = None) -> int:
    environment = dict(os.environ if env is None else env)
    free = fetch_free_models()
    print(f"Kostenlose OpenRouter-Modelle gefunden: {len(free)}")
    routes = build_routes(environment, free)
    if not routes:
        print("::error::Keine Modellroute verfügbar. Hinterlegen Sie OPENROUTER_API_KEY oder OPENAI_API_KEY als Action-Secret.")
        return 3

    for label, model, base_url, api_key in routes:
        print(f"Prüfe Route {label} ...")
        if not ping(base_url, model, api_key):
            print(f"Route {label} nicht erreichbar, nächste Route.")
            continue
        prefix = "" if model.startswith("openrouter/") else ("openrouter/" if "openrouter" in base_url else "")
        chosen = f"{prefix}{model}"
        write_env(environment.get("GITHUB_ENV"), chosen, base_url, api_key)
        print(f"::notice::Modellroute bereit: {label}")
        return 0

    print("::error::Keine Modellroute antwortete. Prüfen Sie Guthaben, Gültigkeit und Modellnamen des Anbieters.")
    return 4


if __name__ == "__main__":
    sys.exit(main())
