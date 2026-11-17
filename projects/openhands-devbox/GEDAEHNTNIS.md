# Projektgedächtnis: openhands-devbox

Dieses Gedächtnis gehört zum Devbox-Projekt und wird nach jedem Sprint ergänzt.

## Läufe

- 2026-11-17 | Profil angelegt; die vorhandene Android-Projektzentrale, Live-App-Ansicht und Free-Route-Hunter-Anbindung sind die Ausgangsbasis für die nächsten Sprints.

## Entscheidungen

- Jeder Sprint bearbeitet genau ein zusammenhängendes Verbesserungspaket.
- Änderungen an Workflows, Secrets und Repository-Einstellungen bleiben ausgeschlossen.

## Befunde

- Die Python-Testbasis umfasst nach Installation von PyYAML 195 erfolgreiche Tests.
- Ein Android-Build ist in der aktuellen Sandbox ohne Android-SDK nicht möglich.

## Wiederhole nicht

- Nicht erneut behaupten, dass die Python-Tests wegen fehlendem PyYAML blockiert sind.
- Nicht erneut versuchen, den Android-Build ohne `ANDROID_HOME` oder `sdk.dir` zu starten.

## Offene Punkte

- Die lokale Projektdefinition muss vor externen GitHub-Actions-Läufen in den Steuer-Branch übernommen werden.
- Nächster Sprint: Android-Projektzentrale und Live-App-Ansicht mit UI-Tests oder einer prüfbaren Zustandsabstraktion absichern.
