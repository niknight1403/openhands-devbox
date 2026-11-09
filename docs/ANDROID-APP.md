# Android-App: OpenHands Devbox

Die App ist die Steuerfläche für die Devbox. Eine Chat-Eingabe startet einen vollständigen
Entwicklungsdurchlauf im Zielprojekt: Planen, Implementieren, Prüfen, Draft-PR, optional
Merge und Folgedurchlauf.

## Was auf dem Gerät läuft und was nicht

Auf dem Handy laufen Oberfläche, Zustandsanzeige und die GitHub-Steuerung. Der Agent selbst
läuft **nicht** auf dem Gerät: OpenHands braucht Docker, einen großen Workspace und einen
Modellschlüssel. Diese Arbeit übernimmt der GitHub-Actions-Lauf in der Devbox.

Damit ist die Autonomie echt, aber indirekt: Die App startet und überwacht den Lauf und
entscheidet nur dort, wo es vorgesehen ist (Merge, Folgedurchlauf). Sie simuliert keine
Agentenschritte und zeigt ausschließlich Zustände, die GitHub tatsächlich meldet.

## Ablauf einer Chat-Eingabe

1. Die App sendet `task`, `profile`, `model`, `target` und `client_run` an den Workflow
   `openhands-task.yml` im Steuer-Repository.
2. Der Workflow legt den Branch `agent/app-<client_run>` im Zielprojekt an und startet die
   Rollen Architekt, Implementierer und Qualitätsprüfer.
3. Die App fragt alle 15 Sekunden den Laufstatus ab und meldet jeden neuen Schritt im Chat.
4. Nach dem Lauf sucht die App den Draft-PR am Branch und zeigt ihn an.
5. Mit aktivem Schalter **Autonom** markiert die App den PR als bereit, wartet auf
   `mergeable` und führt einen squash-Merge aus.
6. Mit **Folgedurchläufen** startet danach ein weiterer Lauf, der das Ergebnis gegen die
   ursprüngliche Aufgabe prüft und Lücken schließt.

## Einrichtung

1. Fine-grained Token auf GitHub erstellen, Zugriff auf Steuer- und Zielprojekt:
   - Actions: read and write (Workflow starten, Status lesen)
   - Contents: read and write (Branch, Dateien)
   - Pull requests: read and write (PR, Merge)
2. APK installieren (Artefakt aus dem Workflow **Android APK** oder Release-Asset).
3. In den Einstellungen Token eintragen, Steuer-Repo (`niknight1403/openhands-devbox`),
   Workflow-Datei (`openhands-task.yml`) und Zielprojekt (`owner/repo`) prüfen.
4. **Token prüfen** antippen. Erst danach Aufträge senden.

Das Token liegt verschlüsselt auf dem Gerät (EncryptedSharedPreferences) und wird nicht
gespeichert, geloggt oder in Meldungen ausgegeben.

## Autonomiestufen

| Stufe | Verhalten |
| --- | --- |
| Standard | Agent liefert einen Draft-PR. Merge macht ein Mensch. |
| Autonom | Merge nach bestätigter Mergebarkeit, ohne Prüfung durch Menschen. |
| Autonom + Folgedurchläufe | Zusätzlich 1 bis 2 Prüf- und Nachbesserungsläufe. |

Autonomie endet dort, wo die Pipeline endet: Ein Lauf schreibt keine Workflows, keine Secrets
und pusht nie direkt auf `main`. Der Guardrail-Sanitizer setzt geschützte Pfade nach jedem Lauf
zurück.

## Grenzen, die die App nicht aufhebt

- Modellguthaben und Anbieterverfügbarkeit entscheiden über den Erfolg eines Laufs. Bleibt das
  Feld **Modell** leer, jagt der Free Route Hunter vor dem Lauf automatisch eine erreichbare
  kostenlose Route und prüft sie mit einem Mini-Aufruf; ohne erreichbare Route startet kein
  Agent. Ein eingetragenes Modell wird stattdessen zuerst geprüft.
- GitHub-Actions-Guthaben und Laufzeitlimits begrenzen die Länge eines Durchlaufs (90 Minuten).
- Ein Agent liefert selten beim ersten Lauf ein fertiges Produkt. Realistisch sind mehrere
  Durchläufe; die App macht sie nur bequem, nicht magisch.
- Ohne grüne Checks merged die App nicht. Das ist Absicht: Sie meldet die Blockade, statt sie
  zu umgehen.

## Lokal bauen

```bash
cd android
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Voraussetzungen: JDK 17, Android SDK (Platform 34, Build-Tools 34.0.0), Gradle-Wrapper ist
im Repository enthalten.

## Aufbau

```
android/app/src/main/java/dev/openhands/devbox/
  data/Settings.kt        Einstellungen, Token verschlüsselt gespeichert
  data/GitHubApi.kt       GitHub-REST: Dispatch, Runs, Steps, PR, Merge
  data/Models.kt          Antwortmodelle
  data/AutonomyEngine.kt  Ablaufsteuerung inklusive Warten und Merge-Entscheidung
  ui/ChatViewModel.kt     Zustand, Chatverlauf, Auftragsstart
  ui/ChatScreen.kt        Chat, Status, Profilwahl, Autonom-Schalter
  ui/SettingsScreen.kt    Einrichtung und Token-Prüfung
  ui/MainActivity.kt      Einstieg und Navigation
```

## Dateien, Fotos und Videos mitschicken (ab 1.2.0)

Über **Datei** neben dem Eingabefeld lassen sich Fotos, Videos und Dokumente
direkt vom Gerät wählen. Die App lädt jede Datei ins Zielprojekt
(`docs/openhands/assets/`, Zweig `main`) und übergibt die Rohadressen im
Workflow-Feld `assets`. Der Lauf lädt sie herunter, legt sie im Draft-PR ab und
nennt dem Agenten Pfad, Typ und Größe.

Grenzen der App: bis zu fünf Dateien je Auftrag, 20 MB je Datei, Upload über die
GitHub-Inhalts-API mit dem gespeicherten Token. Namen werden bereinigt
(`Mein Foto.jpg` → `20261109-034500-Mein-Foto.jpg`), abgelehnte Dateien nennen
den Grund im Chat. Die Chips über dem Eingabefeld zeigen Angehängtes und lassen
sich antippen, um es wieder zu entfernen.
