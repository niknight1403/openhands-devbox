# Auftrag: OpenHands Devbox schrittweise verbessern

Arbeite an der Devbox selbst und setze pro Lauf genau den nächsten sinnvollen
Verbesserungsschritt um. Lies zuerst `projects/openhands-devbox/GEDAEHNTNIS.md`
und den aktuellen Git-Status. Wiederhole keine Punkte unter „Wiederhole nicht“.

## Sprintregeln

1. Prüfe vor Änderungen die betroffenen Android-, Python- und Dokumentationsdateien.
2. Wähle höchstens ein zusammenhängendes Verbesserungspaket mit kleinem, prüfbarem Diff.
3. Bevorzuge in dieser Reihenfolge: Fehler und Sicherheitsprobleme, fehlende Tests,
   unvollständige UX-Zustände, danach Dokumentation und kleinere Verbesserungen.
4. Die Free-Route-Hunter-Grenzen bleiben erhalten: keine Secrets ausgeben, keine
   ungeprüften Provider hinzufügen und im Offline-Modus niemals auf Cloud-Routen ausweichen.
5. Für die Android-App müssen Lade-, Leer- und Fehlerzustände nachvollziehbar sein.
6. Ändere niemals `.github/workflows/`, Secrets, Berechtigungen oder Deployment-Ziele.

## Prüfungen

Führe nach dem Sprint mindestens die betroffenen Tests aus. Wenn verfügbar, führe
zusätzlich `python3 -m unittest discover -s tests -p 'test_*.py' -v` aus. Einen
Android-Build führst du nur bei vorhandenem Android-SDK aus. Dokumentiere jedes
Ergebnis ehrlich; ein fehlendes SDK ist kein Grund, Tests zu verschweigen.

## Abschluss

Aktualisiere `projects/openhands-devbox/GEDAEHNTNIS.md` mit Änderung, Prüfungen,
offenen Punkten und dem nächsten Sprint. Der Lauf endet als Draft-PR; niemals direkt
auf `main` pushen oder mergen.
