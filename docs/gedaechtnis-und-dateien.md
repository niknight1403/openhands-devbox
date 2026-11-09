# Projektgedächtnis, Dateien und freie Werkzeuge

Drei Bausteine sorgen dafür, dass ein Lauf nicht bei null anfängt und dass
Aufträge mit Material arbeiten können: das Projektgedächtnis, die Dateiablage
und das Qualitäts-Gate.

## Projektgedächtnis

Jedes Projekt hat `projects/<slug>/GEDAEHNTNIS.md` mit fünf Abschnitten:

| Abschnitt | Inhalt |
| --- | --- |
| Läufe | automatisch eine Zeile je Lauf: Ergebnis, Route, Branch, PR, Zahl der Dateien |
| Entscheidungen | was gilt, damit es nicht erneut verhandelt wird |
| Befunde | belegte Erkenntnisse über das Zielprojekt |
| Wiederhole nicht | Wege, die schon gescheitert sind |
| Offene Punkte | was ein Mensch entscheiden oder liefern muss |

Gelesen wird beim Start: der Workflow holt die Datei, kürzt sie auf 6000 Zeichen
(neueste Einträge zuerst, Warnungen vorn) und hängt sie an den Auftrag.
Geschrieben wird am Ende: der Workflow trägt den Lauf per GitHub-API in `main`
ein, auch wenn der Lauf gescheitert ist. So überlebt das Wissen auch dann, wenn
ein Draft-PR nie gemergt wird.

Von Hand pflegen:

```bash
python3 scripts/projekt_gedaechtnis.py laden  --projekt cybersarah-control-center
python3 scripts/projekt_gedaechtnis.py eintrag --projekt cybersarah-control-center \
  --art wiederhole-nicht --text "keyless Route pollinations liefert zu langsam"
python3 scripts/projekt_gedaechtnis.py kompakt --projekt cybersarah-control-center --max 25
```

Arten: `lauf`, `entscheidung`, `befund`, `wiederhole-nicht`, `offen`. Gleiche
Einträge werden nicht doppelt aufgenommen, Texte auf 700 Zeichen gekürzt.

## Dateien, Fotos und Videos

Der Workflow hat die Eingabe `assets`: eine URL pro Zeile. Jede Datei wird
geprüft und geladen nach `docs/openhands/assets/` im Zielprojekt, landet also im
Draft-PR und ist für Mensch und Agent sichtbar. Der Auftrag nennt anschließend
Pfad, Typ und Größe jeder Datei.

Grenzen: nur `http` und `https`, nur öffentliche Adressen (kein `localhost`,
keine internen Netze), 40 MB je Datei, keine HTML-Seiten, nur vorgesehene
Dateitypen (Bilder, Videos, Audio, PDF, ZIP, Text). Dateinamen werden bereinigt,
Namenskollisionen weichen auf `name-2.png` aus.

In der Android-App lassen sich Fotos, Videos und Dateien direkt aus dem Chat
anhängen: die App lädt sie ins Zielprojekt hoch und übergibt die Adressen.

## Freie Werkzeuge

`python3 scripts/qualitaets_gate.py` prüft die Devbox mit Werkzeugen, die keine
Lizenz und keinen Schlüssel brauchen: pytest, ruff, bandit, actionlint,
shellcheck und die Python-Syntaxprüfung. Fehlt ein Werkzeug, steht das im
Bericht; der Lauf bricht nicht ab. Der Workflow **Qualitaets-Gate** läuft bei
Push, PR und montags, zeigt den Bericht in der Lauf-Zusammenfassung und legt ihn
als Artefakt ab. Installation der Python-Werkzeuge: `requirements-dev.txt`.

Für Recherche im Netz gibt es `scripts/webtools.py`: `seite --url` liest den
Text einer Seite, `suche --begriff` liefert eine Trefferliste. Beides ohne
Schlüssel, mit denselben Adressgrenzen wie die Dateiablage.

## Was das zusammen bewirkt

Ein Lauf kennt den Stand, wiederholt keine Fehlwege, kann mit Bildern und Videos
arbeiten und hinterlässt messbare Spuren: einen PR mit Befunden, einen
Gedächtniseintrag und einen Qualitätsbericht. Der nächste Lauf beginnt genau
dort.
