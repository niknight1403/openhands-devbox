#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Canvas-Key fehlt. Starte zuerst: bash scripts/bootstrap-codespace.sh" >&2
  exit 1
fi
awk -F= '$1 == "LOCAL_BACKEND_API_KEY" { print substr($0, index($0, "=") + 1); found = 1 } END { if (!found) exit 1 }' .env
