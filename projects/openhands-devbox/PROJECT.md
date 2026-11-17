# OpenHands Devbox

Dieses Projekt ist die Devbox selbst: Android-Steuer-App, Python-Automation,
Projektprofile und Free Route Hunter.

## Relevante Bereiche

- `android/`: Kotlin-/Jetpack-Compose-App mit Chat, Projektzentrale und Live-App-Ansicht.
- `scripts/`: Free Route Hunter, lokaler LLM-Router, Projektgedächtnis und Qualitäts-Gate.
- `config/`: freigegebene Zielrepositories, Route-Katalog und lokale LLM-Konfiguration.
- `projects/`: wiederverwendbare Projektaufträge und Projektgedächtnisse.
- `tests/`: Python-Unit- und Workflow-Tests.

## Prüfungen

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- `python3 -m compileall -q scripts tests`
- `./android/gradlew -p android testDebugUnitTest assembleDebug --no-daemon` (wenn ein Android-SDK verfügbar ist)

## Grenzen

- Keine Secrets, `.env`-Dateien oder Tokens lesen, ändern oder ausgeben.
- Keine Änderungen an `.github/workflows/` oder Repository-Einstellungen.
- Keine direkten Änderungen an `main`; Änderungen bleiben in einem Draft-PR.
- Pro Sprint höchstens ein klar abgegrenztes Verbesserungspaket.
- Bei fehlendem Android-SDK nur die verfügbaren Python-/statischen Checks ausführen und die Grenze dokumentieren.
