# Projektgedächtnis: openhands-devbox

Dieses Gedächtnis gehört zum Devbox-Projekt und wird von den Läufen selbst
fortgeschrieben. Der Workflow trägt jeden Lauf unter „Läufe“ ein; die
Projektentscheidungen und Befunde bleiben hier knapp und prüfbar.

## Läufe

- 2026-11-17 | Profil angelegt; die vorhandene Android-Projektzentrale, Live-App-Ansicht und Free-Route-Hunter-Anbindung sind die Ausgangsbasis für die nächsten Sprints.
- 2026-11-17 | Lauf 44008918185 (failure) | Route `openai/gpt-oss-120b` | Branch `agent/app-devbox-sprint-1-20261117` | PR keiner | Dateien 0 | Ursache: keine nutzbare Modellroute nach Rate-Limits und veralteten Fallback-IDs. [Lauf](https://github.com/niknight1403/openhands-devbox/actions/runs/44008918185)

## Entscheidungen

- Jeder Sprint bearbeitet genau ein zusammenhängendes Verbesserungspaket.
- Änderungen an Workflows, Secrets und Repository-Einstellungen bleiben ausgeschlossen.
- Kostenlose Modellrouten werden vor dem Agentenlauf mit einem echten Mini-Aufruf geprüft; ausgefallene Routen werden für den aktuellen Lauf ausgeschlossen.

## Befunde

- Die Python-Testbasis umfasst nach Installation von PyYAML 196 erfolgreiche Tests.
- Ein Android-Build ist in der aktuellen Sandbox ohne Android-SDK nicht möglich.
- Provider-Modell-IDs ändern sich; Cerebras und Groq verwenden deshalb aktualisierte Fallbacks, eigene Listen können über `HUNTER_MODELS_<ANBIETER>` gesetzt werden.
- Lauf 44008918185 scheiterte im OpenHands-Superagenten an Provider-Rate-Limits beziehungsweise nicht mehr verfügbaren Modell-IDs, nicht an einem Devbox-Codefehler.

## Wiederhole nicht

- Nicht erneut behaupten, dass die Python-Tests wegen fehlendem PyYAML blockiert sind.
- Nicht erneut versuchen, den Android-Build ohne `ANDROID_HOME` oder `sdk.dir` zu starten.
- Nicht dieselben veralteten Cerebras- oder Groq-Modell-IDs als Fallback verwenden.

## Offene Punkte

- Die neue Route-Hunter-Version muss in den nächsten Sprintläufen verwendet und gegen die verfügbaren Repository-Secrets geprüft werden.
- Falls alle kostenlosen Provider kontingentbedingt ausfallen, muss ein Mensch Providerkontingent oder zusätzliche gültige kostenlose Routen bereitstellen.
- Nächster Code-Schritt: Android-Projektzentrale und Live-App-Ansicht mit UI-Tests oder einer prüfbaren Zustandsabstraktion absichern.
