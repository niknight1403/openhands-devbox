#!/usr/bin/env python3
"""Liest die Fehlereignisse eines OpenHands-Laufs und sagt, ob die Modellroute schuld ist.

Die OpenHands-CLI beendet sich bei einem Anbieterfehler mit Exit 0 und legt den
Fehler nur als ``ConversationErrorEvent`` ab. Ohne diese Auswertung merkt der
Workflow erst am Ende, dass die Route unbrauchbar war, und hat dann keinen
Ersatzversuch mehr. Das Skript übersetzt die Ereignisse in klare Exit-Codes.

Exit-Codes:
    0  keine Fehler
    3  Fehler mit Routenbezug (Modell, Kontingent, Netz) -> Ersatzroute versuchen
    4  Fehler ohne Routenbezug -> Lauf abbrechen, Routenwechsel hilft nicht

Nebenwirkung: Es werden ausschließlich maskierte Kurzfassungen ausgegeben,
niemals Zugangsdaten.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

#: Alles, was wie ein Geheimnis aussieht, wird vor der Ausgabe ersetzt.
REDAKTION = re.compile(r"(sk-|ghp_|gho_|ghs_|github_pat_)[A-Za-z0-9_-]+|[A-Za-z0-9_-]{32,}")

#: Hinweise darauf, dass ein anderer Anbieter oder ein anderes Modell hilft.
ROUTEN_MUSTER = re.compile(
    r"litellm\.[A-Za-z0-9_]*Error"
    r"|rate.?limit|free limit|too many requests|quota|no credits|insufficient"
    r"|model_not_found|not a valid model|does not exist|no endpoints found"
    r"|invalid_api_key|authentication|unauthorized|permission"
    r"|context length|maximum context|token limit"
    r"|timeout|timed out|connection (error|refused|reset)|temporarily unavailable"
    r"|\b(HTTP[/ ]1\.[01] )?(429|401|402|403|408|500|502|503|504)\b",
    re.IGNORECASE,
)

#: Bricht die Ausgabe bei sehr vielen Ereignissen nicht aus dem Ruder.
MAX_ANZEIGE = 10


def fehler_aus_datei(pfad: Path) -> list[tuple[str, str]]:
    """Liest eine Ereignisdatei und gibt ``(Code, maskierter Text)`` zurück."""

    try:
        with pfad.open(encoding="utf-8") as strom:
            ereignis = json.load(strom)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(ereignis, dict) or ereignis.get("kind") != "ConversationErrorEvent":
        return []
    code = str(ereignis.get("code", "Unbekannt"))
    roh = " ".join(str(ereignis.get(feld, "")) for feld in ("detail", "message", "msg")).strip()
    return [(code, REDAKTION.sub("<entfernt>", roh)[:400])]


def gespeicherte_gespraeche(basis: Path) -> list[str]:
    """Namen der vorhandenen Gesprächsordner, damit nur neue ausgewertet werden."""

    return sorted(p.name for p in basis.iterdir() if p.is_dir()) if basis.is_dir() else []


def sammle_fehler(basis: Path, nur_neue: set[str] | None = None) -> list[tuple[str, str]]:
    """Sammelt alle Fehlerereignisse, optional nur aus neuen Gesprächen."""

    fehler: list[tuple[str, str]] = []
    for ordner in sorted(glob.glob(str(basis / "*"))):
        gespraech = Path(ordner)
        if nur_neue is not None and gespraech.name in nur_neue:
            continue
        for datei in sorted(Path(ordner, "events").glob("*.json")):
            fehler.extend(fehler_aus_datei(datei))
    return fehler


def ist_routenproblem(text: str) -> bool:
    """Wahr, wenn ein anderer Anbieter das Problem lösen könnte."""

    return bool(ROUTEN_MUSTER.search(text))


def klassifiziere(fehler: list[tuple[str, str]]) -> int:
    """Exit-Code zu einer Fehlerliste."""

    if not fehler:
        return 0
    if all(ist_routenproblem(f"{code} {text}") for code, text in fehler):
        return 3
    return 4


def berichte(fehler: list[tuple[str, str]]) -> int:
    """Gibt die Fehler aus und liefert den passenden Exit-Code."""

    for code, text in fehler[:MAX_ANZEIGE]:
        print(f"::error::OpenHands-Fehler {code}: {text}")
    if len(fehler) > MAX_ANZEIGE:
        print(f"::error::OpenHands meldete {len(fehler)} Fehler, angezeigt sind {MAX_ANZEIGE}.")
    code = klassifiziere(fehler)
    if code == 0:
        print("OpenHands-Event-Pruefung: keine Fehler.")
    elif code == 3:
        print("::warning::OpenHands-Event-Pruefung: Fehler mit Routenbezug, ein Anbieterwechsel kann helfen.")
    else:
        print("::error::OpenHands-Event-Pruefung: Fehler ohne Routenbezug, Lauf wird abgebrochen.")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--basis",
        default=str(Path.home() / ".openhands" / "conversations"),
        help="Ordner mit den OpenHands-Gesprächen (Standard: ~/.openhands/conversations)",
    )
    parser.add_argument("--record", metavar="DATEI", help="Nur den aktuellen Stand speichern und beenden")
    parser.add_argument(
        "--since-state",
        metavar="DATEI",
        help="Nur Gespräche auswerten, die im gespeicherten Stand noch nicht vorkamen",
    )
    args = parser.parse_args(argv)

    basis = Path(args.basis)
    if args.record:
        ziel = Path(args.record)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(gespeicherte_gespraeche(basis)), encoding="utf-8")
        print(f"OpenHands-Stand gespeichert: {ziel}")
        return 0

    bekannt: set[str] | None = None
    if args.since_state:
        quelle = Path(args.since_state)
        try:
            bekannt = set(json.loads(quelle.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            bekannt = None

    return berichte(sammle_fehler(basis, bekannt))


if __name__ == "__main__":
    sys.exit(main())
