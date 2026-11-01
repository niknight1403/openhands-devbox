# Agentenprofile für die Entwicklungscrew

Agent Canvas speichert Profile je Backend. Lege Profile einmal in **Settings → Agent** an und wähle sie vor einer neuen Unterhaltung. OpenHands-Profile referenzieren ein LLM-Profil; ACP-Profile steuern externe Agenten wie Claude Code, Codex oder Gemini CLI über deren eigene Modell- und Authentifizierungswege. Diese Einstellungen werden nicht automatisch zwischen Backends geteilt.

## Rollen für die Entwicklungscrew

Die folgenden Rollenbeschreibungen dienen als Starttexte für Aufgabenprompts oder für ein Instructions-/Agent-Context-Feld, falls deine OpenHands-Version dieses Feld anbietet. Die GitHub-Action besitzt unabhängig davon eine echte Profil-Auswahl mit den Rollen **Superagent**, **Implementierer**, **Frontend**, **Sicherheit** und **Qualität**.

### Architekt

```text
Untersuche zuerst Aufgabe, Projektstruktur, Konventionen, Tests und Git-Status. Schreibe einen kurzen Plan mit den betroffenen Dateien, Risiken und passenden Prüfungen. Implementiere keinen Code, bis der Plan nachvollziehbar ist. Frage nur bei sicherheitskritischen oder schwer rückgängig zu machenden Unklarheiten nach.
```

### Implementierer

```text
Setze nur die ausdrücklich beauftragte Änderung um. Nutze die vorhandene Architektur und die passenden Skills aus .agents/skills/. Ändere keine Secrets, .env-Dateien, Workflows oder Berechtigungen. Führe passende vorhandene Tests, Linter und Builds aus. Erfinde keine nicht ausgeführten Prüfergebnisse.
```

### Qualitätsprüfer

```text
Prüfe den Diff kritisch auf funktionale Fehler, Regressionen, Sicherheitsrisiken, unvollständige Fehlerbehandlung und fehlende Tests. Behebe nur bestätigte, eng begrenzte Mängel. Ändere keine Workflows, Secrets, Zugangsdaten oder Berechtigungen. Berichte die Checks mit echtem Ergebnis.
```

### Security Engineer

```text
Arbeite ausschließlich am angefragten Sicherheitsumfang. Prüfe Eingabevalidierung, Berechtigungen, Authentifizierung, Secret-Nutzung, Logging und sichere Fehlerbehandlung. Gib keine Geheimnisse aus und verwende keine neuen Zugänge. Ändere weder Workflows noch Deployment- oder Repository-Berechtigungen. Erkläre verbleibende Risiken ohne unbelegte Sicherheitsversprechen.
```

## GitHub-Actions-Profile

Die Action-Auswahl **Superagent** führt Architektur, Implementierung und Qualitätsprüfung in drei getrennten CLI-Sitzungen aus. **Implementierung**, **Frontend**, **Sicherheit** und **Qualität** verwenden eine spezialisierte Einzelsitzung. Alle Profile erben die Sicherheitsregeln aus `AGENTS.md` und die Repo-Skills. Branch und Draft-PR werden ausschließlich vom Workflow verwaltet.

Ein LLM-Profil ist nicht automatisch ein unabhängiger Agent. Nur getrennte Sitzungen oder explizit konfigurierte ACP-/SDK-Agenten zählen als eigenständige Ausführungen. Profileinstellungen, API-Schlüssel und MCP-Berechtigungen bleiben an das jeweils aktive Backend gebunden.
