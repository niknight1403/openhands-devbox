# Projektgedächtnis: cybersarah-control-center

Dieses Gedächtnis gehört zum Projekt und wird von den Läufen selbst
fortgeschrieben. Der Workflow trägt jeden Lauf als Zeile unter "Läufe" ein;
alles andere ist bewusst knapp gehalten, damit es gelesen wird.

- **Wiederhole nicht**: was schon versucht wurde und nicht funktioniert hat.
- **Offene Punkte**: was ein Mensch entscheiden oder liefern muss.
- **Entscheidungen**: was gilt, damit es nicht erneut verhandelt wird.
- **Befunde**: belegte Erkenntnisse über das Zielprojekt.

## Läufe

- 2026-11-09 | Lauf 42546288483 (success) | Route openrouter:qwen/qwen3-coder:free | Branch agent/openhands-20261109-013448 | PR #258 | 2 neue Testdateien, Befund 1 und 4 umgesetzt [https://github.com/niknight1403/openhands-devbox/actions/runs/42546288483]
- 2026-11-09 | Lauf 42554062108 (failure) | Route keine | Branch agent/openhands-20261109-030131 | PR keiner | Dateien 1 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/42554062108]
- 2026-11-09 | Lauf 42554381341 (failure) | Route openai/gpt-oss-120b | Branch agent/openhands-20261109-030506 | PR keiner | Dateien 1 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/42554381341]
- 2026-11-09 | Lauf 42556430530 (success) | Route openrouter/stealth/crouton-alpha | Branch agent/app-1794194797098 | PR keiner | Dateien 0 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/42556430530]
- 2026-11-09 | Lauf 42556654773 (success) | Route openrouter/stealth/crouton-alpha | Branch agent/app-1794194952883 | PR keiner | Dateien 0 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/42556654773]
- 2026-11-09 | Lauf 42608553653 (success) | Route openrouter/stealth/crouton-alpha | Branch agent/openhands-20261109-112244 | PR https://github.com/niknight1403/CyberSarah-Control-Center/pull/287 | Dateien 0 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/42608553653]
- 2026-11-10 | Lauf 42804151379 (failure) | Route openrouter/xingchen-agi/xing4.0-29b-a4b:free | Branch agent/openhands-20261110-110236 | PR keiner | Dateien 0 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/42804151379]
- 2026-11-11 | Lauf 43006517002 (failure) | Route openai/gpt-oss-120b | Branch agent/openhands-20261111-104720 | PR keiner | Dateien 0 | Zugang OPENHANDS_GH_PAT [https://github.com/niknight1403/openhands-devbox/actions/runs/43006517002]

## Entscheidungen

- 2026-11-09 | Analyse- und Statusdateien liegen im Zielprojekt (docs/openhands/ANALYSE.md, STATUS.md) und werden per PR gepflegt; der Lauf beginnt mit deren Lektüre.
- 2026-11-09 | Agenten-PRs werden als Squash gemergt (PR #258: 5b1518c), damit die Befundliste auf main linear bleibt.

## Befunde

- 2026-11-09 | Import-Scan: von 410 lib/*.ts-Modulen sind nur 14 ohne Testimport; die Testabdeckung war besser als im Steckbrief angenommen (ANALYSE.md, Befund 2).
- 2026-11-09 | Acht belegte Befunde in ANALYSE.md; Befund 1 (extractJsonObject ohne Tests) und Befund 4 (prompt-contract) sind erledigt.

## Wiederhole nicht

- 2026-11-09 | Nicht erneut behaupten, es gebe flaechendeckend Logik ohne Tests: die Liste ist kurz und in ANALYSE.md belegt.
- 2026-11-09 | Kein Parallelumbau mehrerer Befunde: ein Befund je Lauf, sonst wird der Diff unpruefbar.

## Offene Punkte

- 2026-11-09 | Naechster Schritt laut STATUS.md: Befund 3, ungenutztes Theme lib/neon-pulse-theme.ts entfernen (S, niedriges Risiko).
- 2026-11-09 | Zwei Deploy-Statusmeldungen (create-production-builds.yml) sind auf main dauerhaft rot und unabhaengig von Agenten-PRs; nicht als PR-Fehler werten.
- 2026-11-09 | Lauf 42554062108 endete mit 'failure'; Ursache im Laufprotokoll prüfen, bevor derselbe Weg erneut versucht wird. [https://github.com/niknight1403/openhands-devbox/actions/runs/42554062108]
- 2026-11-09 | Lauf 42554381341 endete mit 'failure'; Ursache im Laufprotokoll prüfen, bevor derselbe Weg erneut versucht wird. [https://github.com/niknight1403/openhands-devbox/actions/runs/42554381341]
- 2026-11-10 | Lauf 42804151379 endete mit 'failure'; Ursache im Laufprotokoll prüfen, bevor derselbe Weg erneut versucht wird. [https://github.com/niknight1403/openhands-devbox/actions/runs/42804151379]
- 2026-11-11 | Lauf 43006517002 endete mit 'failure'; Ursache im Laufprotokoll prüfen, bevor derselbe Weg erneut versucht wird. [https://github.com/niknight1403/openhands-devbox/actions/runs/43006517002]
