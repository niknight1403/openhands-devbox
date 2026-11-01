# OpenHands Devbox 🤖

Autonomer Entwicklungsagent (OpenHands) — **komplett kostenlos, komplett vom Handy steuerbar**. Kein Codespace nötig: OpenHands läuft headless als **GitHub Action**. Öffentliche Repos haben unbegrenzte Actions-Minuten.

## Start vom Handy (3 Tipps)
1. Repo-Seite → **Actions**-Tab → links **OpenHands Task** → **Run workflow**
2. Aufgabe eintippen (natürliche Sprache) → **Run** (Modell/Route leer lassen = automatische Gratis-Kaskade)
3. Fertig: Ergebnis erscheint als **Draft-PR** im Agenten-Villa-Repo — vom Handy reviewen

OpenHands arbeitet auf `niknight1403/Agenten-Villa`, nur auf `agent/*`-Branches, nie direkt auf main.

## Kostenlose Modell-Routen (Kaskade statt Einzelanbieter)
Der Lauf ist nicht mehr an einen Anbieter gebunden. `.github/scripts/waehle_gratis_route.sh`
probiert die Routen in dieser Reihenfolge und nimmt die erste, die auf einen
1-Token-Ping mit HTTP 200 antwortet:

| Priorität | Route | Secret | Kosten |
|---|---|---|---|
| 1 | OpenRouter Free (`qwen/qwen3.8-27b:free`) | `OPENROUTER_API_KEY` | gratis Free-Tier |
| 2 | Google Gemini Flash | `GEMINI_API_KEY` | gratis Free-Tier |
| 3 | Groq (`llama-3.3-70b-versatile`) | `GROQ_API_KEY` | gratis Free-Tier |
| 4 | Cerebras (`gpt-oss-120b`) | `CEREBRAS_API_KEY` | gratis Free-Tier |
| 5 | Mistral (`mistral-small-latest`) | `MISTRAL_API_KEY` | gratis Free-Tier |
| 6 | Hugging Face Router | `HF_TOKEN` | gratis Credits |
| 7 | Pollinations (`text.pollinations.ai`) | **kein Key** | gratis, keyfrei |

**Ein Secret genügt** — und selbst ohne jedes Secret läuft der Lauf über die keyfreie
Pollinations-Route. Fällt ein Anbieter aus (429/401/Timeout), rutscht die Kaskade
automatisch weiter, statt den Job abzubrechen. Erzwungene Route über den
Eingabewert `provider`, eigenes Modell über `model`.

## Einmalige Einrichtung (Settings → Secrets and variables → Actions)
- `OPENHANDS_GH_PAT` — GitHub-Token mit `repo`-Recht (für Checkout, Push, Draft-PR der Agenten-Villa) — **erforderlich**
- Mindestens ein Gratis-Key aus der Tabelle oben — **optional**, empfohlen (schnellere/bessere Modelle als der keyfreie Rückfall)

## Schnelle Erreichbarkeit der UI
- **Headless-Weg (empfohlen, immer verfügbar):** Actions → Run workflow. Kein Port, kein Warten auf einen Container.
- **Codespace-Weg:** `.devcontainer` ist vorbereitet. Port 3000 wird automatisch als
  *„OpenHands UI"* weitergeleitet und im Browser geöffnet; `docker-compose.yml` hat
  einen Healthcheck, damit der Port erst als bereit gilt, wenn OpenHands wirklich antwortet.
- Port-Sichtbarkeit ist bewusst **private** (nicht public): die OpenHands-UI hängt am
  Docker-Socket des Codespace und darf nicht offen im Netz stehen. Zugriff vom Handy
  erfolgt über die GitHub-Anmeldung im Browser.
- Standard-Route im Codespace: `OPENHANDS_LLM_MODEL` / `OPENHANDS_LLM_BASE_URL` setzen,
  sonst OpenRouter Free; ohne Key springt der Container auf einen der anderen Gratis-Keys.
- Das Codespace-Kontingent (120 Kernstunden) **resettet monatlich** — das `.devcontainer` bleibt im Repo.

## Aufgabenteilung
- **OpenHands (dieses Repo):** kleine Jobs, Experimente, spontane Aufgaben — jederzeit vom Handy
- **Autonom-Wache (Mo/Do 9 Uhr):** reguläre Agenten-Villa-Sprints, CI-Wartung

## Kosten: 0 €
Actions auf öffentlichen Repos: unbegrenzt kostenlos. Freie Modell-Routen, GitHub gratis. Keine Dienste mit Zahlungspflicht.

## Wichtig
- Nach Review: Draft-PR normal mergen — niemals direkt auf main pushen
- Bei Fehlern: Actions-Log zeigt jede probierte Route (`OK` / `HTTP <code>`) und den Grund
