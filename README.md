# OpenHands Devbox

Eine mobile, autonome Entwicklungsumgebung auf Basis der offiziellen OpenHands Agent Canvas-Oberfläche und eines GitHub-Actions-Superagenten. Die Canvas-Oberfläche läuft im Codespace auf Port **8000**. Der Actions-Workflow kann Aufgaben manuell vom Handy starten und liefert Codeänderungen ausschließlich als **Draft-PR** auf einem `agent/*`-Branch.

## Was enthalten ist

- **Android-App:** installierbare Steuer-App (`android/`). Eine Chat-Eingabe startet einen vollständigen Entwicklungsdurchlauf, zeigt die Agentenschritte live, öffnet den Draft-PR und kann ihn im Autonom-Modus mergen und nachbessern lassen.
- **Agent Canvas:** aktuelle OpenHands-Steueroberfläche mit LLM-/Agent-Profilen, MCP-Server-Einstellungen und Projektkontext.
- **Superagenten-Lauf:** drei getrennte OpenHands-CLI-Durchläufe — Architektur/Plan, Implementierung und Qualitätsreview — mit gemeinsamem Workspace.
- **Rollenprofile:** zusätzlich auswählbare Modi für Implementierung, Frontend, Sicherheit und Qualität.
- **Skills-Pack:** projektübergreifend übertragbare Skills unter `.agents/skills/`; die Action kopiert sie bei jedem Lauf in das Zielprojekt.
- **Free Route Hunter:** sucht vor jedem Lauf automatisch eine erreichbare kostenlose Modellroute aus den hinterlegten Secrets, prüft sie mit einem echten Mini-Aufruf und protokolliert das Ergebnis als Artefakt.
- **LLM-Autopilot:** prüft alle sechs Stunden alle erreichbaren Routen samt Werkzeugaufruf, veröffentlicht den Status auf dem Branch `autopilot/status` und übernimmt konfigurierte Plugin-Packs. Fällt eine Route mitten im Lauf aus, jagt der Workflow sofort Ersatz und wiederholt die Rolle.
- **Sicherheitsnetz:** Agenten dürfen im Zielprojekt weder Workflows noch Secrets-Dateien ändern. Der Workflow verwirft solche Änderungen, erstellt einen Branch und öffnet bei Änderungen einen Draft-PR. Er pusht nie auf `main`.
- **Zugriffsschutz:** Canvas verwendet einen lokal generierten Backend-API-Key. Der Codespaces-Port erhält private Sichtbarkeit als Standard; selbst wenn ein Port versehentlich öffentlich gestellt wird, ist der Backend-Zugriff weiterhin durch den API-Key geschützt.

Der Agenten-Workflow bearbeitet standardmäßig `niknight1403/Agenten-Villa`. Das Ziel wird bewusst nur aus einer festen Liste freigegebener Repositories gewählt (Workflow-Eingabe `target`), damit ein Tippfehler oder Prompt keine beliebigen Repositories mit dem hinterlegten PAT öffnen kann.

Vor jedem Lauf jagt der **Free Route Hunter** (`scripts/free_route_hunter.py`) eine Route, die gerade wirklich antwortet: Wunschmodell zuerst, sonst alle Anbieter, für die ein Secret hinterlegt ist — OpenRouter mit live gelesenen `:free`-Modellen, dazu Gemini, Groq, Cerebras, Mistral, GitHub Models und Hugging Face —, am Ende eine schlüsselfreie Reserve. Jeder Kandidat wird mit einem echten Mini-Aufruf geprüft, sortiert nach Tool-Calling, Code-Eignung und Kontextfenster. Nur eine antwortende Route startet den Agenten; sonst bricht der Lauf mit der Liste aller geprüften Kandidaten ab. Details: [Free Route Hunter](docs/FREE-ROUTE-HUNTER.md).

## Autopilot: dauerhaft funktionsfähige Routen

Der **LLM Autopilot** (`.github/workflows/llm-autopilot.yml`) läuft alle sechs Stunden und prüft jede erreichbare Route mit zwei echten Aufrufen: einer beantwortet einen Mini-Prompt, der zweite verlangt einen Werkzeugaufruf. Nur eine bestätigte `tool_calls`-Antwort gilt als Werkzeugroute. Das Ergebnis steht als Artefakt und auf dem Branch `autopilot/status`; der Agentenlauf lädt diesen Status vorab und prüft bestätigte Routen zuerst.

Weitere Routen kommen ohne Codeänderung dazu: lokal in `config/route-catalog.json` oder entfernt über die Repository-Variable `AUTOPILOT_CATALOG_URLS`. Plugin-Packs im AgentSkills-Format werden aus `config/plugin-packs.json` geprüft und bei `mode: install` in das Zielprojekt kopiert. Fällt eine Route mitten im Lauf aus, jagt der Workflow eine Ersatzroute (bis zu zwei Versuche) statt abzubrechen. Details und Stellschrauben: [LLM-Autopilot](docs/LLM-AUTOPILOT.md).

## Android-App bauen und installieren

Die App liegt in `android/` (Kotlin, Jetpack Compose, minSdk 26). Der Workflow **Android APK** baut bei jeder Änderung an `android/` ein Debug-APK und legt es als Artefakt `openhands-devbox-apk` ab; bei einem Tag wird es zusätzlich als Release-Asset veröffentlicht. Lokal:

```bash
cd android && ./gradlew assembleDebug
```

In der App in den Einstellungen einen Fine-grained Token (Actions, Contents, Pull requests: je read and write) eintragen, Steuer-Repo und Zielprojekt prüfen, **Token prüfen** antippen. Danach genügt im Chat eine Aufgabe. Details, Ablauf und Grenzen: [Android-App](docs/ANDROID-APP.md).

Der Autonom-Modus ist eine bewusste Entscheidung: Ohne ihn bleibt jeder Lauf als Draft-PR zur Prüfung liegen. Erst der Schalter **Autonom** mergebarer PRs macht aus dem Chat einen durchlaufenden Auftrag; mit **Folgedurchläufen** prüft ein weiterer Lauf das Ergebnis und schließt Lücken.

## Vom Android-Handy starten

1. Öffne dieses Repository in der GitHub-App und gehe zu **Actions → OpenHands Task → Run workflow**.
2. Gib die Aufgabe ein. Wähle ein Rollenprofil; **Superagent** ist der Standard. Optional kannst du ein Modell im LiteLLM-Format angeben, zum Beispiel `openrouter/provider/model`.
3. Starte den Lauf. Verfolge die Phasen in den Action-Logs und prüfe den resultierenden Draft-PR vor dem Merge.

Ein leer gelassenes Aufgabenfeld startet den begrenzten Autonom-Wache-Auftrag. Geplant ist ein Lauf am Montag und Donnerstag um **07:00 UTC**; die lokale Uhrzeit verschiebt sich mit Sommer-/Winterzeit.

## Agent Canvas im Codespace

Öffne dieses Repository als GitHub Codespace. Beim Start erzeugt `scripts/bootstrap-codespace.sh` einen zufälligen Canvas-API-Key in der Git-ignorierten Datei `.env`, jagt eine erreichbare Gratis-Route und startet Agent Canvas mit dieser Route (`HUNTER_DISABLE=1` schaltet die Suche ab, `HUNTER_REFRESH=1` sucht neu). Port **8000** wird mit privater Sichtbarkeit weitergeleitet. Der Container hat Zugriff auf den Repository-Workspace und Docker, um isolierte Agent-Container zu starten; verwende den Codespace daher nur mit vertrauenswürdigen Projekten.

Für die erste Anmeldung zeige den Schlüssel im Codespace-Terminal mit `bash scripts/show-canvas-key.sh` an und gib ihn in der Canvas-Anmeldemaske ein. Kopiere ihn nicht in Repository-Dateien, Chat-Prompts oder Logs. Die Datei bleibt im Codespace gespeichert und wird nicht in Git übernommen.

Die Einstellungen sind backend-spezifisch. In Agent Canvas:

- **Settings → LLM:** Modellanbieter, Modell und API-Key konfigurieren.
- **Settings → Agent:** OpenHands- oder ACP-Agentenprofile anlegen und auswählen.
- **Customize → MCP Servers:** benötigte externe Tools verbinden und die Verbindung testen.
- **Customize → Skills:** Skills verwalten oder eine vertrauenswürdige Skill-Quelle hinzufügen.

Siehe [Agentenprofile](docs/AGENT-PROFILES.md) und [Integrationen und Connectoren](docs/INTEGRATIONS.md) für die mitgelieferten Profile und sichere Einrichtung.

## Einmalige GitHub-Einrichtung

Lege die folgenden Secrets in **Settings → Secrets and variables → Actions** dieses Repositorys an:

- `OPENROUTER_API_KEY` — Hauptroute; der Hunter liest daraus live alle kostenlosen Modelle.
- `OPENHANDS_GH_PAT` — GitHub-Token mit Zugriff auf das Zielrepository `Agenten-Villa`; für Branch-Push und Draft-PR.

Jedes weitere Secret erweitert die Kaskade automatisch, ohne Codeänderung. Reihenfolge und Grenzen stehen in [Free Route Hunter](docs/FREE-ROUTE-HUNTER.md):

- `GEMINI_API_KEY` oder `GOOGLE_API_KEY` — Google-AI-Studio-Free-Tier.
- `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `MISTRAL_API_KEY` — kostenlose Kontingente.
- `HF_TOKEN` — Hugging Face Inference Providers.
- `GH_MODELS_TOKEN` — GitHub Models.
- `OPENAI_API_KEY` — kostenpflichtig, nur wenn ausdrücklich erlaubt.

Der Workflow **Free Route Check** prüft die Kaskade zusätzlich täglich um 05:00 UTC und auf Knopfdruck, ohne einen Agenten zu starten. Sein Report zeigt, welche Route aktuell antwortet und welche Anbieter ohne Schlüssel dastehen.

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
