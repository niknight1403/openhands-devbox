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

exec docker compose up -d
