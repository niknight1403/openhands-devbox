# Projekte

Ein Projekt bündelt alles, was ein Agentenlauf über ein Zielrepository wissen
muss: welches Repository gemeint ist, welche Kommandos dort zählen, wo die
heiklen Stellen liegen und mit welchem Prompt gearbeitet wird.

## Aufbau

```
projects/<slug>/
  project.env   Maschinenlesbar: Zielrepository, Standardprofil, Kadenz
  PROJECT.md    Steckbrief für den Agenten (Stack, Kommandos, Grenzen)
  PROMPT.md     Der eingesetzte Auftrag, mehrstufig und wiederholbar
```

Der Slug ist der Verzeichnisname in Kleinschreibung mit Bindestrichen. Das
Zielrepository steht in `project.env` in der Schreibweise von GitHub, denn
genau dieser Wert wird ausgecheckt.

## Wie ein Lauf ein Projekt benutzt

Im Workflow `OpenHands Task` gibt es den Eingabewert `project`. Ist er gesetzt,
dann

1. liest der Schritt `Projekt laden` `project.env`,
2. prüft er das Zielrepository gegen `config/targets.txt`,
3. setzt er `TARGET_REPO` für alle folgenden Schritte,
4. hängt er `PROMPT.md` und `PROJECT.md` an den Auftrag des Laufs.

Ohne `project` verhält sich der Workflow wie vorher: Zielrepository direkt
gewählt, Auftrag aus dem Eingabefeld oder der Autonom-Wache-Text.

## Ein neues Projekt anlegen

1. Ordner `projects/<slug>/` mit den drei Dateien anlegen.
2. Zielrepository in `config/targets.txt` eintragen. Ohne Eintrag bricht der
   Lauf ab, bevor Modellkontingent verbraucht wird.
3. Wenn das Projekt regelmäßig laufen soll, einen Aufrufer wie
   `cybersarah-autopilot.yml` anlegen, der `openhands-task.yml` per
   `workflow_call` startet.
4. `python3 -m unittest tests.test_projekte` ausführen. Der Test prüft, dass
   Steckbrief, Prompt und Whitelist zusammenpassen.
