# Auftrag: CyberSarah Control Center analysieren, optimieren, perfektionieren

Du arbeitest im Repository CyberSarah-Control-Center. Dieser Auftrag gilt bei
jedem Lauf und wird nach und nach abgearbeitet. Prüfe zuerst, was schon
geschehen ist, und mach dann genau einen Schritt weiter.

## Schritt 0: Stand prüfen (jeder Lauf)

Lies, sofern vorhanden:

- `docs/openhands/ANALYSE.md` (Befundliste mit Prioritäten)
- `docs/openhands/STATUS.md` (was erledigt ist, was offen blieb, nächster Schritt)

Gibt es diese Dateien noch nicht, ist dieser Lauf der Analyselauf.
Steht dort ein nächster Schritt, bearbeite genau den.

## Phase A: Analyse (nur wenn `docs/openhands/ANALYSE.md` fehlt)

Ändere keinen Produktcode. Erkunde das Repository gezielt: Aufbau, Kommandos
für Typen, Tests und Lint, die Logikmodule in `lib/`, die Router in `server/`,
die Testsuite in `tests/`.

Schreibe `docs/openhands/ANALYSE.md` mit höchstens zehn Befunden, sortiert nach
Wirkung geteilt durch Aufwand. Jeder Befund nennt:

- **Was** konkret fehlt oder falsch ist, mit Datei und Zeilenbezug,
- **Warum** es zählt, in einem Satz,
- **Aufwand** als S, M oder L,
- **Risiko** der Behebung als niedrig, mittel oder hoch,
- **Prüfung**, woran man danach erkennt, dass es behoben ist.

Nimm keine Vermutungen als Befund auf. Was du nicht belegen kannst, kommt in
einen Abschnitt "Offene Fragen" statt in die Liste.

## Phase B: Optimieren (Folgeläufe)

Setze den obersten offenen Befund um, höchstens drei zusammenhängende
Änderungen. Halte dich an den vorhandenen Stil, ergänze Tests für neue Logik
und lass `npm run check` und `npm run test` laufen. Berichte ehrlich, welche
Prüfungen liefen und welche nicht.

Kann ein Befund nicht sauber umgesetzt werden, weil eine Entscheidung fehlt,
kommentiere ihn in `ANALYSE.md` mit dem Grund und nimm den nächsten.

## Phase C: Perfektionieren (Dauerziel)

"Perfekt" heißt hier nicht makellos, sondern messbar besser. Diese Latte gilt
für jeden Beitrag:

1. `npm run check` läuft ohne Fehler.
2. `npm run test` läuft ohne neue Fehlschläge. Weniger Tests als vorher ist kein
   Fortschritt.
3. Neue Fachlogik liegt in `lib/` und hat einen Test in `tests/`.
4. Kein neuer `any`-Typ und keine neue stillschweigend verschluckte Ausnahme.
5. Die Dokumentation, die du berührst, beschreibt danach den echten Stand.

Schreibe am Ende jedes Laufs `docs/openhands/STATUS.md`: Datum, erledigte
Befunde, ausgeführte Prüfungen mit Ergebnis, offene Punkte, nächster Schritt.
Diese Datei ist das Gedächtnis der Läufe. Ohne sie fängt jeder Lauf von vorn an.

## Grenzen

- Nur Draft-Pull-Request, niemals direkt auf `main`.
- Keine Änderungen an `.github/workflows/`, `.github/scripts/` oder
  Repository-Einstellungen.
- Keine Deploys, keine Datenbankmigration, keine Käufe, keine Nachrichten.
- Keine Zugangsdaten lesen, kopieren oder ausgeben, auch nicht aus `.env`.
- Keine Abhängigkeiten austauschen und keine Formatierungswelle über hunderte
  Dateien. Ein Diff, den ein Mensch in wenigen Minuten prüfen kann, ist besser
  als ein großer Umbau.

## Bericht

Kurz und prüfbar: welcher Schritt, welche Änderung, welche Prüfung mit welchem
Ergebnis, was bleibt offen. Zahlen nennen, nicht behaupten.
