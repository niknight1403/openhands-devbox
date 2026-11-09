# Free Route Hunter

Der Hunter beantwortet eine einzige Frage, bevor ein Agent startet: **Welche
kostenlose Modellroute antwortet gerade wirklich?** Statt einen Modellnamen fest
zu verdrahten, baut `scripts/free_route_hunter.py` die Kandidatenliste aus den
Zugangsdaten, die tatsächlich im Repository hinterlegt sind, prüft jeden
Kandidaten mit einem echten Mini-Aufruf und gibt erst die funktionierende Route
an OpenHands weiter.

## Warum das nötig ist

Kostenlose Modellrouten verschwinden schnell: ein `:free`-Modell wird aus der
Liste genommen, ein Tageskontingent ist um 09:00 aufgebraucht, ein Anbieter
antwortet mit HTTP 429. Ein fest eingetragener Modellname führt dann zu einem
Lauf, der minutenlang startet und still scheitert. Der Hunter macht daraus eine
prüfbare Entscheidung: entweder eine Route mit HTTP 2xx, oder ein klarer Abbruch
mit der Liste aller geprüften Kandidaten.

## Wie die Kaskade aufgebaut ist

1. **Wunschmodell zuerst.** Ist im Workflow ein `model` angegeben (oder per
   `--model`), wird ausschließlich diese Route geprüft. Ein toter Modellname
   fällt sofort auf.
2. **Anbieter mit Secret.** Jeder hinterlegte Schlüssel erweitert die Jagd
   automatisch. Fehlende Secrets werden übersprungen, nicht als Fehler
   behandelt.
3. **OpenRouter dynamisch.** Die freien Modelle werden live aus
   `https://openrouter.ai/api/v1/models` gelesen: nur Modelle, deren Prompt- und
   Completion-Preis `0` ist und deren Kontextfenster mindestens 16.000 Token
   groß ist. Damit ist der Hunter nicht auf Modellnamen aus der
   Trainingszeit angewiesen.
4. **Schlüsselfreie Reserve.** Zuletzt wird eine Route ohne Schlüssel geprüft,
   damit ein Lauf nicht allein wegen fehlender Guthaben scheitert.

## Sortierung: was zuerst geprüft wird

| Rang | Kriterium | Grund |
| --- | --- | --- |
| 1 | bezahlte Anbieter zuletzt | der Hunter soll gratis bleiben |
| 2 | Anbieterpriorität (`HUNTER_PREFER` schlägt Standard) | eigene Erfahrung vor Heuristik |
| 3 | Tool-Calling unterstützt | ohne Tools bricht ein agentischer Lauf ab |
| 4 | Code-Signale (`coder`, `qwen3`, `deepseek`, `gpt-oss`, `kimi`, …) | Agent soll Code schreiben |
| 5 | Größe (kleine Modelle abgewertet, große bevorzugt) | Qualität pro Durchlauf |
| 6 | Kontextfenster | mehr Platz für Repository-Kontext |
| 7 | Name | stabile, wiederholbare Reihenfolge |

Die Prüfung läuft in Vierergruppen parallel, in Rangreihenfolge. Die erste
Antwort aus der höchsten Gruppe gewinnt, deshalb bleibt das Ergebnis
reproduzierbar und der Lauf trotzdem kurz.

## Einmalige Einrichtung: Secrets

Nur ein einziges Secret ist nötig, alles andere ist optional:

| Secret | Rolle |
| --- | --- |
| `OPENROUTER_API_KEY` | Hauptroute; der Hunter liest daraus alle freien Modelle |
| `GEMINI_API_KEY` oder `GOOGLE_API_KEY` | Google-AI-Studio-Free-Tier |
| `GROQ_API_KEY` | kostenloses Minutenkontingent, sehr schnell |
| `CEREBRAS_API_KEY` | kostenloses Tageskontingent |
| `MISTRAL_API_KEY` | Free-Tier über La Plateforme |
| `HF_TOKEN` | Hugging-Face-Inference-Providers, Monatsquote |
| `GH_MODELS_TOKEN` | GitHub Models, kostenloses Kontingent für öffentliche Repos |
| `OPENAI_API_KEY` | kostenpflichtig, nur mit `HUNTER_ALLOW_PAID=1` oder erzwungenem Modell |
| `OPENHANDS_GH_PAT` | kein Modellschlüssel: nur für Branch-Push und Draft-PR in fremden Zielprojekten; im eigenen Repository greift der eingebaute `GITHUB_TOKEN` |

Ein Schlüssel wird ausschließlich an seinen eigenen Anbieter geschickt. Der
Hunter gibt keine Schlüssel aus, schreibt keine in Berichte und nennt im Log nur
`OK`/`--` mit HTTP-Code und Latenz.

## Aufruf

```bash
# jagen: schreibt LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, LLM_ROUTE_NAME, LLM_ROUTE_PROVIDER
python3 scripts/free_route_hunter.py

# nur zeigen, was geprüft würde (keine Modellaufrufe)
python3 scripts/free_route_hunter.py --list

# Anbieter bevorzugen und Report schreiben
python3 scripts/free_route_hunter.py --prefer groq,openrouter --report route-report.json

# Zusammenfassung für GitHub Actions
python3 scripts/free_route_hunter.py --summary --report "$RUNNER_TEMP/route-report.json"
```

Weitere Schalter: `--model` (Route erzwingen), `--timeout`, `--max-per-provider`,
`--min-context`, `--env-file`, `--json`, `--include-paid`.

Stellschrauben per Umgebung: `HUNTER_PREFER`, `HUNTER_TIMEOUT`,
`HUNTER_MAX_PER_PROVIDER`, `HUNTER_MIN_CONTEXT`, `HUNTER_ALLOW_PAID`,
`HUNTER_MODEL`, `HUNTER_REPORT`.

## Exit-Codes

| Code | Bedeutung |
| --- | --- |
| `0` | Route gefunden und geschrieben |
| `3` | keine Kandidaten: kein passendes Secret vorhanden |
| `4` | alle Kandidaten geprüft, keine antwortete |

## Wo der Hunter eingebunden ist

- **`.github/workflows/openhands-task.yml`**: Schritt „Gratis-Route jagen“ vor
  dem Agentenlauf. Der Report liegt als Artefakt `route-report` beim Lauf, die
  Route steht in der Step-Summary.
- **`.github/workflows/free-route-check.yml`**: prüft die Kaskade täglich um
  05:00 UTC und auf Knopfdruck, ohne einen Agenten zu starten. So sieht man vor
  dem nächsten Sprint, welche Anbieter noch liefern.
- **`scripts/bootstrap-codespace.sh`**: jagt beim Codespace-Start eine Route und
  legt sie in der Git-ignorierten `.env` ab, damit Agent Canvas ohne manuelles
  Eintragen startet (`HUNTER_DISABLE=1` schaltet das ab, `HUNTER_REFRESH=1`
  sucht neu).

## Wenn eine Route mitten im Lauf ausfällt

Die OpenHands-CLI beendet sich bei Anbieterfehlern mit **Exit 0** und legt den
Fehler nur als `ConversationErrorEvent` ab. Ein `set -e` merkt davon nichts, und
der Lauf wäre am Ende rot, ohne je eine Ersatzroute probiert zu haben.

Deshalb wertet `scripts/openhands_events.py` nach jedem Rollenversuch die neuen
Gesprächsereignisse aus. Es speichert vorher den Stand der Gesprächsordner und
liest danach nur die neu hinzugekommenen, damit ein alter Fehler nicht erneut
zuschlägt. Der Exit-Code sagt dem Workflow, was zu tun ist:

| Code | Bedeutung | Reaktion im Workflow |
| --- | --- | --- |
| `0` | keine Fehler | Rolle gilt als erfolgreich |
| `3` | Fehler mit Routenbezug (Kontingent, Modell, Auth, Netz) | Route in `HUNTER_EXCLUDE`, neue Route jagen, Versuch wiederholen (bis `ROUTE_RETRIES`, Standard 2) |
| `4` | Fehler ohne Routenbezug (Werkzeug, Plan, Datei) | sofortiger Abbruch, ein Anbieterwechsel hilft nicht |

Ausgegeben werden nur maskierte Kurzfassungen; Schlüssel und lange Zeichenketten
ersetzt das Skript durch `<entfernt>`. Eine globale Prüfung über alle Gespräche
am Ende gibt es bewusst nicht mehr: Sie würde Fehler bereits verworfener Routen
erneut melden und einen geretteten Lauf fälschlich rot machen.

## Hinweise aus dem Autopilot-Status

Der Autopilot kann erprobte Routen als Hinweise mitgeben (`HUNTER_STATUS_FILE`).
Sie bringen ihre Modelle in die Jagd und übernehmen die Werkzeugeignung aus dem
Status. Sie überstimmen die Eignung aber **nicht** mehr: bis Version davor
standen Hinweise immer vorn, wodurch eine veraltete Empfehlung die schlüsselfreie
Route `pollinations` vor alle echten Anbieter schob. Der Agentenlauf scheiterte
dann am Kontingent, obwohl Schlüssel für Groq, Cerebras und Gemini vorhanden
waren. Jetzt gilt die normale Sortierung, Hinweise sind nur eine zusätzliche
Modellquelle.

## Grenzen

- Ein HTTP 2xx beim Mini-Aufruf garantiert keinen guten Lauf. Es beweist nur,
  dass Route, Schlüssel und Modellname zusammen funktionieren.
- Kostenlose Kontingente sind begrenzt und ändern sich ohne Ankündigung. Ein
  Superagenten-Lauf mit drei Rollen verbraucht mehr als ein einzelner Aufruf.
- Der Hunter wählt nur unter den Anbietern, für die ein Secret existiert. Ohne
  Schlüssel bleibt die schlüsselfreie Reserve, die oft ausgelastet ist.
- Die Heuristik sortiert nach Eignungssignalen im Modellnamen, nicht nach
  gemessener Codequalität.

## Tests

`tests/test_free_route_hunter.py` prüft Preisauswertung, Discovery, Ranking,
Wunschmodell-Auflösung, Kaskadenaufbau, Abbruchverhalten, Env-Ausgabe und dass
kein Schlüssel in Report oder Log landet. `tests/test_openhands_events.py` prüft
die Fehlerklassifikation, die Maskierung und die Eingrenzung auf neue Gespräche.
`tests/test_workflow_routes.py` hält fest, dass der Workflow wirklich je Versuch
auswertet und Fehler ohne Routenbezug sofort abbricht. Die Tests laufen offline,
ohne Netzwerkaufruf.
