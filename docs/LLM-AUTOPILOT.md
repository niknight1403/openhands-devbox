# LLM-Autopilot

Der Autopilot hält die Devbox dauerhaft mit funktionierenden kostenlosen
Modell-, Werkzeug- und Skill-Routen versorgt. Er läuft geplant, prüft echte
Antworten statt Prospektdaten und schreibt einen Status, den Agentenlauf und
Android-App weiterverwenden.

## Was der Autopilot automatisch macht

| Aufgabe | Umsetzung |
| --- | --- |
| Routen finden | eingebaute Anbieter + `config/route-catalog.json` + entfernte Kataloge (`AUTOPILOT_CATALOG_URLS`) |
| Antwort prüfen | echter Chat-Aufruf mit `max_tokens=1` je Kandidat |
| Werkzeugrouten prüfen | zweiter Aufruf mit `tools` und `tool_choice:auto`; nur eine echte `tool_calls`-Antwort gilt als Werkzeugroute |
| Ausfall überbrücken | Agentenlauf jagt bei einem Modellfehler sofort eine Ersatzroute und wiederholt die Rolle (bis zu zwei Versuche) |
| Wissen festhalten | Status-JSON als Artefakt und auf dem Branch `autopilot/status`; der Agentenlauf lädt ihn als Hinweisliste |
| Plugin-Packs | konfigurierte Skill-Packs werden geladen, ihr Frontmatter geprüft und bei `mode: install` ins Zielprojekt kopiert |

## Taktung

`LLM Autopilot` (`.github/workflows/llm-autopilot.yml`) läuft **alle sechs
Stunden** und auf Knopfdruck. Jeder Lauf ist unabhängig: keine Zustandsdatei im
Repository außer dem veröffentlichten Status.

Der Status landet unter
`https://raw.githubusercontent.com/niknight1403/openhands-devbox/autopilot/status/status.json`
und enthält ausschließlich Anbietername, Modell, Basis-URL, HTTP-Code, Latenz und
die Ergebnisse der Werkzeugprüfung — keine Schlüssel, keine Prompts.

## Unbekannte Routen hinzufügen

Ein „unbekannter" Anbieter ist ein OpenAI-kompatibler Endpunkt, den der
eingebaute Katalog nicht kennt. Zwei Wege:

**Lokal** in `config/route-catalog.json`:

```json
{
  "routes": [
    {
      "name": "mein-anbieter",
      "base_url": "https://api.example.com/v1",
      "models": ["modell-a", "modell-b"],
      "key_envs": ["MEIN_ANBIETER_KEY"],
      "litellm_prefix": "openai/"
    }
  ]
}
```

**Entfernt** über eine Repository-Variable `AUTOPILOT_CATALOG_URLS`
(kommagetrennte HTTPS-JSON-URLs). Entfernte Kataloge dürfen ausschließlich
schlüsselfreie Routen deklarieren: `key_envs` wird dort abgewiesen, damit ein
fremder Katalog keine Repository-Secrets an einen eigenen Endpunkt umleiten kann.
Schlüsselgebundene Custom-Routen gehören in den versionierten lokalen Katalog.

Regeln, die der Autopilot selbst durchsetzt:

- nur `http(s)`-Basis-URLs, `name` und mindestens ein Modell sind Pflicht,
- Einträge mit `key_envs` werden nur geprüft, wenn der Schlüssel gesetzt ist,
- jede Route wird mit einem echten Aufruf getestet, bevor sie als brauchbar gilt,
- ein toter Katalog oder eine tote Route erzeugt eine Warnung, keinen Abbruch.

Ein Schlüssel geht ausschließlich an die Basis-URL seines eigenen Eintrags.

## Werkzeugrouten

Ein Modell, das keine Werkzeuge aufruft, ist für OpenHands unbrauchbar. Deshalb
sendet die Werkzeugprüfung eine Anfrage mit einer Funktionsdefinition und prüft,
ob die Antwort `tool_calls`, `function_call` oder `finish_reason: tool_calls`
enthält. Ergebnis:

- `tools_ok: true` → Route wird im Ranking zuerst geführt und vom Hunter
  bevorzugt,
- `tools_ok: false` → Route bleibt nutzbar, wird aber nachrangig behandelt.

Im Live-Test bestätigte die schlüsselfreie Reserve tatsächlich einen
Werkzeugaufruf; solche Beobachtungen stehen im Status, nicht in einer
Behauptung im README.

## Plugin-Packs

`config/plugin-packs.json` beschreibt Packs im AgentSkills-Format:

```json
{
  "packs": [
    { "name": "anthropic-skills", "repo": "anthropics/skills", "ref": "main",
      "path": "skills", "mode": "validate", "select": ["frontend-design"] }
  ]
}
```

- `mode: validate` prüft nur (`name` und `description` im Frontmatter, Dateigröße
  begrenzt) und kopiert nichts.
- `mode: install` kopiert die als gültig erkannten `SKILL.md` in
  `workspace/.agents/skills/<skill>/`, von wo OpenHands sie im Lauf sieht.

Der Standard ist bewusst `validate`: fremde Skill-Texte werden erst übernommen,
wenn Inhalt und Lizenz geprüft sind. Es werden nur öffentliche Repositorys ohne
Zugangsdaten gelesen.

## Selbstheilung im Agentenlauf

`openhands-task.yml` prüft nach jeder Rolle den Log auf Modellfehler
(`litellm.*Error`, `no credits remaining`, `429`, `model_not_found`,
`invalid_api_key`). Tritt einer auf:

1. Die ausgefallene Route kommt in `HUNTER_EXCLUDE`.
2. Der Hunter jagt eine Ersatzroute (Autopilot-Hinweise zuerst, dann Kaskade).
3. Die neuen `LLM_*`-Werte werden per `--shell-export` geladen und die Rolle
   läuft erneut.
4. Nach zwei erfolglosen Ersatzversuchen bricht der Lauf mit klarer Meldung ab.

Der Ausschluss gilt nur für den laufenden Lauf; die nächste Ausführung beginnt
wieder mit der vollen Kaskade.

## Stellschrauben

| Variable | Standard | Wirkung |
| --- | --- | --- |
| `AUTOPILOT_MAX_ROUTES` | `24` | Obergrenze der Prüfungen pro Lauf |
| `AUTOPILOT_MAX_PER_PROVIDER` | `5` | Modelle je Anbieter |
| `AUTOPILOT_TIMEOUT` | `20` | Sekunden je Aufruf |
| `AUTOPILOT_TOOL_PROBE` | `1` | Werkzeugtest an/aus |
| `AUTOPILOT_CATALOG` | `config/route-catalog.json` | lokaler Zusatzkatalog |
| `AUTOPILOT_CATALOG_URLS` | leer | entfernte Kataloge (Repository-Variable) |
| `AUTOPILOT_STATUS` | leer | Zielpfad des Status-JSON |
| `HUNTER_STATUS_FILE` | leer | Hinweisliste für den Hunter |
| `HUNTER_EXCLUDE` | leer | Routen, die nicht erneut geprüft werden |
| `ROUTE_RETRIES` | `2` | Ersatzversuche je Rolle |

## Grenzen

- Der Autopilot erfindet keine Anbieter. Er prüft, was konfiguriert ist oder aus
  eingebauten, dokumentierten Quellen stammt.
- Ein `2xx` beweist Funktion, nicht Qualität: ein Lauf kann trotz erreichter
  Route unbefriedigend programmieren.
- Kostenlose Kontingente bleiben flüchtig. Der Autopilot macht Ausfälle
  sichtbar und überbrückbar, nicht unmöglich.
- Skill-Packs sind Textdateien. Sie werden strukturell geprüft, nicht inhaltlich
  auditiert; `mode: install` bleibt deshalb eine bewusste Entscheidung.

## Tests

`tests/test_llm_autopilot.py` prüft Katalog-Auswertung, Kandidatenaufbau,
Werkzeugerkennung, Ranking, Skill-Prüfung, Pack-Validierung, Installation,
Status-Erzeugung und Exit-Codes — vollständig offline.
