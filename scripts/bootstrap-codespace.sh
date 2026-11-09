#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Persistiert nur innerhalb des Codespace-Workspaces; .env ist von Git ausgeschlossen.
touch .env
chmod 600 .env
if ! grep -q '^LOCAL_BACKEND_API_KEY=.' .env; then
  sed -i '/^LOCAL_BACKEND_API_KEY=/d' .env
  KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  printf 'LOCAL_BACKEND_API_KEY=%s\n' "$KEY" >> .env
fi

# Lokale Offline-Route: config/local-llm.env beschreibt den eigenen Endpunkt
# (Ollama, LiteLLM-Proxy). Im Offline-Modus schreibt das Skript die Route in die
# .env und die Cloud-Jagd entfällt vollständig; ein nicht erreichbarer Router
# wird gemeldet, aber nie durch einen Cloud-Anbieter ersetzt.
ROUTE_MODE="cloud"
if [ -f "$ROOT/scripts/local_llm_router.py" ]; then
  ROUTE_MODE="$(python3 "$ROOT/scripts/local_llm_router.py" --apply --env-file .env 2>/dev/null || echo cloud)"
fi
chmod 600 .env

if [ "$ROUTE_MODE" = "local" ]; then
  export LLM_OFFLINE=1
  echo "Lokale Offline-Route aktiv (config/local-llm.env). Alle Agentenaufrufe gehen an den lokalen Endpunkt."
  echo "Prüfen mit: python3 scripts/local_llm_router.py --check"
elif [ "${HUNTER_DISABLE:-0}" != "1" ]; then
  # Cloud-Modus (LLM_OFFLINE=0): der Hunter prüft die kostenlosen Anbieter mit
  # einem echten Mini-Aufruf und schreibt die erste antwortende Route in die
  # Git-ignorierte .env. Fehlende Anbieter-Schlüssel werden übersprungen.
  # Abschalten mit HUNTER_DISABLE=1, erneut suchen mit HUNTER_REFRESH=1.
  if [ "${HUNTER_REFRESH:-0}" = "1" ] || ! grep -q '^LLM_MODEL=.' .env; then
    python3 "$ROOT/scripts/free_route_hunter.py" \
      --env-file .env \
      --report "${TMPDIR:-/tmp}/free-route-report.json" \
      --timeout "${HUNTER_TIMEOUT:-12}" \
      || echo "Hinweis: keine Gratis-Route erreichbar. Route in den Canvas-Einstellungen eintragen."
    chmod 600 .env
  fi
fi

exec docker compose up -d
