# OpenHands Devbox

Eine mobile, autonome Entwicklungsumgebung auf Basis der offiziellen OpenHands Agent Canvas-Oberfläche und eines GitHub-Actions-Superagenten. Die Canvas-Oberfläche läuft im Codespace auf Port **8000**. Der Actions-Workflow kann Aufgaben manuell vom Handy starten und liefert Codeänderungen ausschließlich als **Draft-PR** auf einem `agent/*`-Branch.

## Was enthalten ist

- **Agent Canvas:** aktuelle OpenHands-Steueroberfläche mit LLM-/Agent-Profilen, MCP-Server-Einstellungen und Projektkontext.
- **Superagenten-Lauf:** drei getrennte OpenHands-CLI-Durchläufe — Architektur/Plan, Implementierung und Qualitätsreview — mit gemeinsamem Workspace.
- **Rollenprofile:** zusätzlich auswählbare Modi für Implementierung, Frontend, Sicherheit und Qualität.
- **Skills-Pack:** sechs projektübergreifend übertragbare Skills unter `.agents/skills/`, darunter [automatisches Refactoring](.agents/skills/openhands-devbox-automated-refactoring/SKILL.md); die Action kopiert sie bei jedem Lauf in das Zielprojekt.
- **Sicherheitsnetz:** Agenten dürfen im Zielprojekt weder Workflows noch Secrets-Dateien ändern. Der Workflow verwirft solche Änderungen, erstellt einen Branch und öffnet bei Änderungen einen Draft-PR. Er pusht nie auf `main`.
- **Zugriffsschutz:** Canvas verwendet einen lokal generierten Backend-API-Key. Der Codespaces-Port erhält private Sichtbarkeit als Standard; selbst wenn ein Port versehentlich öffentlich gestellt wird, ist der Backend-Zugriff weiterhin durch den API-Key geschützt.

Der Agenten-Workflow bearbeitet standardmäßig `niknight1403/Agenten-Villa`. Das Ziel wird absichtlich nicht frei eingegeben, damit ein Tippfehler oder Prompt keine beliebigen Repositories mit dem hinterlegten PAT öffnen kann.

## Vom Android-Handy starten

1. Öffne dieses Repository in der GitHub-App und gehe zu **Actions → OpenHands Task → Run workflow**.
2. Gib die Aufgabe ein. Wähle ein Rollenprofil; **Superagent** ist der Standard. Optional kannst du ein Modell im LiteLLM-Format angeben, zum Beispiel `openrouter/provider/model`.
3. Starte den Lauf. Verfolge die Phasen in den Action-Logs und prüfe den resultierenden Draft-PR vor dem Merge.

Ein leer gelassenes Aufgabenfeld startet den begrenzten Autonom-Wache-Auftrag. Geplant ist ein Lauf am Montag und Donnerstag um **07:00 UTC**; die lokale Uhrzeit verschiebt sich mit Sommer-/Winterzeit.

## Agent Canvas im Codespace

Öffne dieses Repository als GitHub Codespace. Beim Start erzeugt `scripts/bootstrap-codespace.sh` einen zufälligen Canvas-API-Key in der Git-ignorierten Datei `.env` und startet Agent Canvas. Port **8000** wird mit privater Sichtbarkeit weitergeleitet. Der Container hat Zugriff auf den Repository-Workspace und Docker, um isolierte Agent-Container zu starten; verwende den Codespace daher nur mit vertrauenswürdigen Projekten.

Für die erste Anmeldung zeige den Schlüssel im Codespace-Terminal mit `bash scripts/show-canvas-key.sh` an und gib ihn in der Canvas-Anmeldemaske ein. Kopiere ihn nicht in Repository-Dateien, Chat-Prompts oder Logs. Die Datei bleibt im Codespace gespeichert und wird nicht in Git übernommen.

Die Einstellungen sind backend-spezifisch. In Agent Canvas:

- **Settings → LLM:** Modellanbieter, Modell und API-Key konfigurieren.
- **Settings → Agent:** OpenHands- oder ACP-Agentenprofile anlegen und auswählen.
- **Customize → MCP Servers:** benötigte externe Tools verbinden und die Verbindung testen.
- **Customize → Skills:** Skills verwalten oder eine vertrauenswürdige Skill-Quelle hinzufügen.

Siehe [Agentenprofile](docs/AGENT-PROFILES.md) und [Integrationen und Connectoren](docs/INTEGRATIONS.md) für die mitgelieferten Profile und sichere Einrichtung.

## Einmalige GitHub-Einrichtung

Lege die folgenden Secrets in **Settings → Secrets and variables → Actions** dieses Repositorys an:

- `OPENROUTER_API_KEY` — bevorzugte Modellroute für Actions.
- `OPENAI_API_KEY` — optionaler Fallback, falls kein OpenRouter-Key gesetzt ist.
- `OPENHANDS_GH_PAT` — GitHub-Token mit Zugriff auf das Zielrepository `Agenten-Villa`; für Branch-Push und Draft-PR.

Lege Modell-Keys, die der Codespace benötigt, zusätzlich als Codespaces-Secrets an oder trage sie direkt in den Canvas-Einstellungen ein. Der Canvas-API-Key wird lokal generiert und benötigt kein GitHub-Secret. Der Modellanbieter-Key wird im Actions-Lauf dem OpenHands-Prozess für LLM-Aufrufe bereitgestellt; verwende dafür Keys mit möglichst engem Kontingent und ohne zusätzliche Anbieterrechte. Rohe Agentenlogs und Fehlerdetails werden nicht in Actions-Logs gestreamt, und der Aufgabenprompt wird nicht in Commit- oder PR-Metadaten kopiert. Zugangsdaten gehören trotzdem nie in Dateien, Prompts, Action-Eingaben oder Logs. Der Actions-PAT wird beim Checkout nicht an OpenHands übergeben und erst für den abschließenden Push-/PR-Schritt bereitgestellt.

## Erweiterungen: Skills, MCP und Pakete

Das mitgelieferte Pack ist ein **AgentSkills-kompatibles Repository-Paket** und braucht keinen Marktplatz. MCP-Server werden absichtlich nicht automatisch mit fremden Tokens oder weitreichenden Rechten installiert: verbinde nur Anbieter, denen du vertraust, und vergib minimal nötige Berechtigungen. OpenHands unterstützt je nach Server Streamable HTTP, SSE und stdio; Streamable HTTP ist für Remote-Server die empfohlene Transportart. Erste OAuth-Anmeldungen benötigen eine interaktive Bestätigung.

Enterprise-Marktplätze und SDK-Plugins sind optionale OpenHands-Funktionen und nicht mit dem normalen Skills-Pack gleichzusetzen. Diese Devbox verspricht nicht, beliebige Integrationen ohne Anbieterzugangsdaten, Berechtigungen oder Lizenz freizuschalten.

## Kosten und Grenzen

GitHub-Actions-Kontingente, Modellverfügbarkeit und Preise hängen von GitHub und dem gewählten Modellanbieter ab. Ein Modell mit `:free` kann sich ändern oder begrenzt sein; prüfe den Anbieter vor längeren Läufen. Der Superagent führt bis zu drei eigenständige Modell-Sitzungen aus und kann daher mehr Zeit und Modellkontingent verbrauchen als ein einzelner Lauf.

## Sicherheitsregeln

- Nie direkt auf `main` pushen oder mergen; erst den Draft-PR prüfen.
- Niemals Agenten-Logs oder Aufgaben mit API-Schlüsseln, Tokens oder privaten Daten befüllen.
- Nur vertrauenswürdige MCP-Server und Skills installieren. Tools können je nach Berechtigung externe Daten lesen oder Aktionen ausführen.
- Workflow-Dateien und Secret-Dateien im Zielprojekt sind für den Agenten gesperrt. Die Action setzt geschützte Pfade nach dem Lauf zurück, erkennt Renames/Kopien und entfernt erkannte Credential-Werte aus geänderten Dateien, ohne die Werte zu loggen. Das ist eine zusätzliche Guardrail und kein Ersatz für Review und begrenzte Provider-Keys.
- Der Docker-Socket gibt dem OpenHands-Container weitreichenden Zugriff innerhalb des Codespaces. Port **8000** auf **Private** belassen und keinen nicht vertrauenswürdigen Code dort ausführen. Der Backend-API-Key bleibt auch bei versehentlich öffentlichem Port erforderlich.

## Quellen

- [OpenHands Agent Canvas](https://github.com/OpenHands/OpenHands)
- [OpenHands MCP-Einstellungen](https://docs.openhands.dev/openhands/usage/settings/mcp-settings)
- [OpenHands Skills und Plugins](https://docs.openhands.dev/enterprise/skills-and-plugins)
- [OpenHands Agentenprofile](https://docs.openhands.dev/openhands/usage/agent-canvas/agent-profiles)
- [OpenHands Container-Fehlerbehebung und Skills-Mounts](https://docs.openhands.dev/openhands/usage/troubleshooting/troubleshooting)
