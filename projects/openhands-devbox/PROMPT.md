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

## Kompetenz-Wächter

Prüfe vor jedem Lauf anhand des Auftrags, welche Modell-, Test-, Recherche- oder Build-Fähigkeiten gebraucht werden. Nutze vorhandene Agentenrollen, lokale Skill-Packs und bei Web-Recherche die vorhandenen Werkzeuge in `control/scripts/webtools.py`; prüfe im Autopilot-Bericht, ob eine Modellroute echte Tool-Aufrufe unterstützt. Die wiederkehrende Autopilot-Prüfung und der Free-Route-Hunter dürfen nur konfigurierte oder fest eingebaute Routen nutzen und bei Ausfall auf eine bestätigte Route wechseln.

Kopiere nur die kuratierten lokalen Skill-Packs automatisch. Fehlen normale projektlokale Abhängigkeiten, ergänze sie mit dem vorhandenen Paketmanager samt Lockfile und prüfe die Integration. Externe Packs bleiben im Standardmodus `validate`; ändere diesen Modus nicht ohne Prüfung von Inhalt und Lizenz. Installiere keine beliebigen MCP-Server, Plugins oder ausführbaren Web-Tools, fordere keine Berechtigungen an und lege keine Zugangsdaten an. Wenn eine notwendige Fähigkeit danach fehlt, benenne den konkreten Blocker, nutze einen sicheren vorhandenen Ersatz oder schlage eine eng begrenzte, freizugebende Integration vor. Behaupte nie, ein Werkzeug sei verfügbar, wenn es nicht tatsächlich geprüft wurde.

## Prüfungen

Führe nach dem Sprint mindestens die betroffenen Tests aus. Wenn verfügbar, führe
zusätzlich `python3 -m unittest discover -s tests -p 'test_*.py' -v` aus. Einen
Android-Build führst du nur bei vorhandenem Android-SDK aus. Dokumentiere jedes
Ergebnis ehrlich; ein fehlendes SDK ist kein Grund, Tests zu verschweigen.

## Abschluss

Aktualisiere `projects/openhands-devbox/GEDAEHNTNIS.md` mit Änderung, Prüfungen,
offenen Punkten und dem nächsten Sprint. Der Lauf endet als Draft-PR; niemals direkt
auf `main` pushen oder mergen.
