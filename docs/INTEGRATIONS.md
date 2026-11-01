# Integrationen und Connectoren

OpenHands erweitert Agenten über MCP-Server und Agent-Profile. Konfiguriere Integrationen in Agent Canvas unter **Customize → MCP Servers**; für Modellauswahl und Schlüssel nutze **Settings → LLM** beziehungsweise **Settings → Secrets**. Diese Einstellungen sind backend-spezifisch und werden nicht automatisch zwischen lokalem Backend, Codespace, Cloud oder anderen Agent-Servern synchronisiert.

## Sinnvolle Connector-Kategorien

Installiere nur die Werkzeuge, die der konkrete Arbeitsablauf braucht:

- **Quellcode und Review:** GitHub MCP für Issues, Pull Requests und Repository-Metadaten. Für Schreibzugriff eng begrenzte Repository-Berechtigungen vergeben.
- **Projektverwaltung:** Linear, Jira oder ein anderes Issue-System für Tickets und Status. Schreibrechte nur bei tatsächlichem Automatisierungsbedarf aktivieren.
- **Kommunikation und Wissen:** Slack, Notion oder vergleichbare Systeme, zunächst möglichst mit Nur-Lesen-Rechten.
- **Recherche:** Websuche/Fetch für öffentliche Dokumentation. Tavily ist in OpenHands als Suchanbieter dokumentiert; der API-Key gehört in die LLM-Einstellungen, nie in eine Skill-Datei.
- **Lokale Entwicklungswerkzeuge:** Test-, Browser- oder Datenbank-MCP-Server nur dann ergänzen, wenn Projekt und Laufzeit sie wirklich benötigen. Ein MCP-Server mit Shell-, Dateisystem- oder Datenbankrechten kann Änderungen außerhalb des Codes auslösen.

Die konkreten Server-URLs, MCP-Implementierungen, verfügbaren Tools und Authentifizierungsarten unterscheiden sich nach Anbieter. Verwende dessen offizielle Dokumentation statt unbekannte Endpunkte aus Beispielen zu übernehmen.

## Sichere Verbindung

1. Öffne **Customize → MCP Servers → Add custom server** und wähle Streamable HTTP, SSE oder stdio passend zum Server. Für entfernte Server empfiehlt OpenHands Streamable HTTP.
2. Trage Endpoint und Authentifizierung direkt in der Oberfläche ein. Nutze Bearer/API-Key oder OAuth nur nach Prüfung der Anbieterberechtigungen. Schreibe Credentials nicht in dieses Repository oder in Aufgabenprompts.
3. Teste die Verbindung und prüfe, welche Tools bereitgestellt werden. Deaktiviere oder entferne nicht benötigte Server.
4. Starte für neue Skills oder MCP-Änderungen eine neue Unterhaltung; bestehende Konversationen erhalten ihre Toolliste beim Start.
5. Beachte, dass OAuth beim ersten Zugriff eine interaktive Nutzerautorisierung erfordern kann und deshalb nicht immer headless geeignet ist.

## Skill-Pack und Marketplace

Dieses Repository liefert Skills im AgentSkills-Format unter `.agents/skills/`. Skills enthalten Anweisungen, keine Zugangsdaten. Für ein anderes Zielrepository kopiert der Actions-Workflow das Pack vor dem Start dorthin.

OpenHands Enterprise kann Git-basierte Plugin-Marktplätze verwalten. SDK-Plugins können Skills, Hooks, MCP-Konfigurationen, Agents und Slash-Commands bündeln. Das ist nicht dasselbe wie ein beliebiges Repository-Skill-Pack und ist nicht automatisch in jeder Self-Hosted-Edition verfügbar. Prüfe Edition und Lizenz, bevor du einen Marketplace oder Plugin-Workflow voraussetzt.
