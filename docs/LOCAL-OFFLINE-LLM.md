# Lokale Offline-Route

Die Devbox kann den LLM-Verkehr vollständig auf einen eigenen Router umlegen:
Ollama, ein LiteLLM-Proxy oder ein anderer OpenAI-kompatibler Endpunkt. Im
Offline-Modus gibt es genau eine Route. Cloud-Anbieter werden weder geprüft
noch als Ersatz eingesetzt, wenn der lokale Endpunkt schweigt.

## Verbindungsparameter

| Variable | Wert | Bedeutung |
| --- | --- | --- |
| `LLM_BASE_URL` | `http://host.docker.internal:11434/v1` | Endpunkt aus Sicht des Canvas-Containers |
| `LLM_MODEL` | `openai/qwen2.5-coder:7b` | LiteLLM-ID: Präfix `openai/` plus Modell des Routers |
| `LLM_API_KEY` | `local-dummy-key` | wird lokal ignoriert, das Client-SDK verlangt ihn |
| `LLM_OFFLINE` | `1` | nur lokale Route, kein Cloud-Fallback |

Die Quelle der Werte ist `config/local-llm.env`. Umgebungsvariablen derselben
Namen überschreiben die Datei, ohne dass sie geändert werden muss. Eine
maschinenlesbare Fassung inklusive Grenzen liegt in `config/local-llm.json`.

Vom Host aus heißt dieselbe Route `http://127.0.0.1:11434/v1`, ein
LiteLLM-Proxy liegt typisch auf `http://127.0.0.1:4000/v1`, eine zweite Maschine
im LAN auf `http://192.168.1.20:11434/v1`.

## Ablauf beim Start

`scripts/bootstrap-codespace.sh` erzeugt zuerst den lokalen Backend-Key und
ruft dann `scripts/local_llm_router.py --apply` auf. Bei `LLM_OFFLINE=1`
schreibt das Skript die sechs Routenvariablen in die ignorierte `.env`
(`LLM_OFFLINE`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_ROUTE_NAME`,
`LLM_ROUTE_PROVIDER`) und die Cloud-Jagd entfällt. Bei `LLM_OFFLINE=0` bleibt
der bisherige Weg mit dem Free Route Hunter.

`docker-compose.yml` setzt dieselben Werte als Vorgabe. Damit startet der
Container auch ohne `.env` gegen den lokalen Router; ein `OPENROUTER_API_KEY`
wird nicht mehr als Ersatz herangezogen.

## Prüfen

```bash
ollama serve                     # Router starten (falls nicht als Dienst)
ollama pull qwen2.5-coder:7b     # Modell laden

python3 scripts/local_llm_router.py --check          # Modellliste, Chat, Werkzeugaufruf
python3 scripts/local_llm_router.py --check --json   # maschinenlesbar
python3 scripts/local_llm_router.py --print-env       # Werte, Schlüssel maskiert
```

Exit-Codes: `0` Route antwortet, `5` Router nicht erreichbar (kein
Cloud-Fallback), `7` Konfiguration ungültig.

## Was die Sperren tun

- `LOCAL_LLM_STRICT=1` lehnt jede Basis-URL ab, die nicht Loopback, privates
  Netz, `localhost`, `*.local` oder `host.docker.internal` ist. Für einen
  bewusst entfernten Router `LOCAL_LLM_STRICT=0` setzen.
- `scripts/free_route_hunter.py` baut bei `LLM_OFFLINE=1` keine
  Cloud-Kandidaten, prüft nur die lokale Route und bricht mit Exit 5 ab, wenn
  sie nicht antwortet. Der Ersatzversuch im Agentenlauf kann damit nicht ins
  Netz ausweichen.
- `scripts/llm_autopilot.py` akzeptiert `http://` nur für lokale Endpunkte und
  lädt im Offline-Modus ausschließlich lokale Katalogeinträge
  (`config/route-catalog.json`, Eintrag `local-ollama`).
- `scripts/local_llm_router.py` schreibt die `.env` idempotent: wiederholte
  Läufe erzeugen keine doppelten Einträge, andere Schlüssel bleiben erhalten.

## Grenzen

- GitHub-Actions-Läufe können keinen Router auf dem eigenen Rechner erreichen.
  Dort bleibt `LLM_OFFLINE=0`; für Offline-Betrieb in CI braucht es einen
  Self-Hosted-Runner mit Zugriff auf den Endpunkt.
- Die Android-App verbindet sich direkt mit dem Canvas-Backend. Für Betrieb
  außerhalb des Rechners muss der Router erreichbar sein (VPN oder LAN), sonst
  bleibt die App offline.
- Kleine lokale Modelle sind bei Werkzeugaufrufen und langen Kontexten
  schwächer als Cloud-Modelle. Der Autopilot weist eine Route deshalb separat
  als Werkzeugroute aus; `--check` zeigt `Werkzeuge nein`, wenn das Modell keine
  Funktionsaufrufe liefert. Ohne Werkzeugroute führt OpenHands keine Datei-
  Änderungen aus.

## Tests

```bash
python3 -m unittest tests.test_local_llm_router -v
```

Die Tests laufen ohne Netzwerk: sie ersetzen den HTTP-Aufruf, prüfen die
Adresssperre, die `.env`-Idempotenz, den Offline-Gate von Hunter und Autopilot
sowie den Bootstrap-Start.
