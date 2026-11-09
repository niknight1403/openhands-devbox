# Projektsteckbrief: CyberSarah Control Center

Dieser Steckbrief geht jedem Agentenlauf als Kontext mit. Er ersetzt keine
eigene Erkundung des Repositorys, sondern verhindert die teuren Anfängerfehler.

## Was das Projekt ist

Zentrale Plattform hinter CyberSarah: Produktiv-App für Web und Android mit
eigenem Node-Server, Multi-Provider-KI-Anbindung und einem Master-Agenten.
Betrieben auf Render unter `app.cybersarah-ki.com`, Datenbank ist Neon-Postgres.
Stand beim Anlegen dieses Steckbriefs: v2.4.0, Sprint 193, rund 2340 Dateien.

## Aufbau

- `app/`, `components/`, `hooks/`: Expo mit expo-router, Web-Export und
  Capacitor für Android. Styling über NativeWind, Farben ausschließlich über
  Tokens aus `lib/design/future-glass.ts`.
- `server/`: tRPC-Router und Serverlogik. `server/_core/` enthält LLM-Aufrufe,
  Auth und Kontext. `server/orchestrator/` ist der Master-Agent mit
  Werkzeugregistry und State-Store.
- `lib/`: reine Logikmodule, überwiegend ohne Netz und ohne Dateisystem, dadurch
  gut testbar. Neue Fachlogik gehört hierher, nicht in die Router.
- `drizzle/`: Schema und Migrationen. `tests/`: Vitest-Suite.
- `.github/workflows/`: über 60 Workflows für Deploy, Diagnose, Revenue und
  Agenten. Für Agentenläufe gesperrt.

## Kommandos, die zählen

| Zweck | Kommando |
| --- | --- |
| Typen prüfen | `npm run check` |
| Tests | `npm run test` |
| Lint und Format | `npm run lint`, `npm run format` |
| Systemprüfung | `npm run verify:system` |
| Web-Export-Smoke | `npm run web:smoke` |
| Schema und Migration | `npm run db:push` |

`npm run check` und `npm run test` sind die Mindestlatte. Wer sie nicht laufen
lässt, kann seinen Beitrag nicht als fertig bezeichnen.

## Heikle Bereiche

- **Migrationen:** `drizzle/` nur ergänzen, niemals bestehende Migrationen
  umschreiben. Produktivdaten hängen daran.
- **Zugangsdaten:** `.env`, `.env.bak-dbfix`, `secrets-backup.tar.gz.gpg` und
  alles unter `server/_core/` mit Schlüsselbezug bleiben unangetastet. Keine
  Werte lesen, kopieren oder ausgeben.
- **Workflows:** `.github/workflows/` und `.github/scripts/` sind für
  Agentenläufe gesperrt. Der Workflow stellt geschützte Pfade nach dem Lauf
  wieder her.
- **Deploy:** Render-Deploy, Datenbankmigration und PM2 laufen über eigene
  Workflows. Ein Agentenlauf löst sie nicht aus.
- **Sprache:** Oberfläche und Dokumentation sind deutsch. Neue Texte ebenso.

## Wo der größte Hebel liegt

Aus Sicht der Devbox, in dieser Reihenfolge:

1. **Logik ohne Testabdeckung:** Module in `lib/` mit echter Fachlogik, aber
   ohne Test. Dort ist eine kleine Ergänzung viel wert und riskiert nichts.
2. **Fehlerpfade in Routern:** `server/*-router.ts` prüft Eingaben
   unterschiedlich streng. Vereinheitlichung wirkt sofort, ist aber sorgfältig
   zu belegen.
3. **Zustand im UI:** Lade-, Leer- und Fehlerzustände sind nicht überall
   vorhanden. Kleine, klar abgegrenzte Nachbesserungen mit sichtbarem Nutzen.
4. **Dokumentation, die vom Code abweicht:** `README.md`, `NEXT_STEPS.md` und
   `docs/` beschreiben teils ältere Stände.

Nicht sinnvoll sind breite Umbauten, Dependency-Wechsel oder
Formatierungswellen über hunderte Dateien. Sie erzeugen Diff-Rauschen ohne
prüfbaren Nutzen.
