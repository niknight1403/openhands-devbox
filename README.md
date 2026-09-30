# OpenHands Devbox 🤖

Autonomer Entwicklungsagent (OpenHands) als **GitHub Codespace** — komplett kostenlos, ideal vom Handy (Termux/Browser) steuerbar.

## Warum Codespace?
Docker läuft nicht auf Android/Termux. Ein Codespace bringt Docker eingebaut mit. Öffentliche Repos verbrauchen das Free-Kontingent nicht (120 Kernstunden/Monat bleiben für andere Projekte frei).

## Start vom Handy (2 Klicks)
1. Auf dieser Repo-Seite: grüner **`<> Code`**-Button → **Codespaces** → **Create codespace on main**
2. Warten (erste ~2 Minuten, Image-Pull), dann im unteren Panel → **Ports** → Port **3000** → Globus-Symbol 🌐 öffnet die OpenHands-UI im Handy-Browser

OpenHands startet dank `postStartCommand` automatisch mit.

## Einmalige Einrichtung (wichtig)
Auf github.com → Settings → Codespaces → **Secrets** (gilt für dieses Repo):
- `OPENROUTER_API_KEY` — dein OpenRouter-Key (kostenlose Modelle, wie in der Agenten-Villa)
- `OPENHANDS_GH_PAT` — GitHub-PAT mit `repo`-Recht, damit OpenHands Branches/PRs anlegen kann

In der OpenHands-UI unter Einstellungen → LLM:
- Provider: **OpenRouter**
- Model: ein `:free`-Modell (z. B. `deepseek/deepseek-chat-v3-0324:free`)

## Arbeiten mit der Agenten-Villa
- Repository beim Task angeben: `niknight1403/Agenten-Villa`
- Änderungen nur über `agent/*`-Branches mit Draft-PR — gleiche Regeln wie für die Autonom-Wache
- Abgrenzung: OpenHands für kleine Jobs/Experimente; reguläre Sprints fährt die Autonom-Wache (Mo/Do 9 Uhr)

## Kosten: 0 €
Codespaces (öffentliches Repo), OpenRouter Free, GitHub gratis. Docker-Compose-Stack lokal in diesem Repo, keine bezahlten Dienste.

## Wichtig
Nach der Arbeit: Codespace stoppen (`Codespaces` → ⋯ → Stop) — nur Laufzeit zählt, gestoppte Codespaces kosten nichts.
