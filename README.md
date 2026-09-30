# OpenHands Devbox 🤖

Autonomer Entwicklungsagent (OpenHands) — **komplett kostenlos, komplett vom Handy steuerbar**. Kein Codespace nötig: OpenHands läuft headless als **GitHub Action**. Öffentliche Repos haben unbegrenzte Actions-Minuten.

## Start vom Handy (3 Tipps)
1. Repo-Seite → **Actions**-Tab → links **OpenHands Task** → **Run workflow**
2. Aufgabe eintippen (natürliche Sprache), Modell vorausgewählt lassen → **Run**
3. Fertig: Ergebnis erscheint als **Draft-PR** im Agenten-Villa-Repo — vom Handy reviewen

OpenHands arbeitet auf `niknight1403/Agenten-Villa`, nur auf `agent/*`-Branches, nie direkt auf main. Freies DeepSeek-Modell über OpenRouter (gleiche Free-Route wie die Agenten-Villa).

## Einmalige Einrichtung (Settings → Secrets and variables → Actions)
Zwei Secrets in diesem Repo hinterlegen:
- `OPENROUTER_API_KEY` — dein OpenRouter-Key (kostenlose Modelle)
- `OPENHANDS_GH_PAT` — GitHub-Token mit `repo`-Recht (für Checkout, Push, Draft-PR der Agenten-Villa)

Ohne `OPENROUTER_API_KEY` bricht der Lauf kontrolliert ab und sagt es im Log.

## Aufgabenteilung
- **OpenHands (dieses Repo):** kleine Jobs, Experimente, spontane Aufgaben — jederzeit vom Handy
- **Autonom-Wache (Mo/Do 9 Uhr):** reguläre Agenten-Villa-Sprints, CI-Wartung

## Fallback: Codespaces
Das Codespace-Kontingent (120 Kernstunden) **resettet monatlich** — das `.devcontainer` bleibt im Repo; wenn wieder Quota da ist, funktioniert der UI-Weg weiter.

## Kosten: 0 €
Actions auf öffentlichen Repos: unbegrenzt kostenlos. OpenRouter Free, GitHub gratis. Keine Dienste mit Zahlungspflicht.

## Wichtig
- Nach Review: Draft-PR normal mergen — niemals direkt auf main pushen
- Bei Fehlern: Actions-Log zeigt jeden OpenHands-Schritt (`--headless` loggt alles)
