"""Dauerhaftes Projektgedaechtnis der Devbox.

Ein Lauf ist nur so gut wie das, was der vorherige hinterlassen hat. Dieses
Werkzeug pflegt je Projekt eine Markdown-Datei `projects/<slug>/GEDAEHNTNIS.md`
mit festen Abschnitten. Geschrieben wird nach jedem Lauf (automatisch durch den
Workflow) und bei Bedarf von Hand; gelesen wird beim Start des naechsten Laufs,
gekuerzt auf ein Zeichenbudget, damit der Prompt nicht unbegrenzt waechst.

Abschnitte: Laeufe, Entscheidungen, Befunde, Wiederhole nicht, Offene Punkte.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ABSCHNITTE = ("Läufe", "Entscheidungen", "Befunde", "Wiederhole nicht", "Offene Punkte")
ARTEN = {
    "lauf": "Läufe",
    "entscheidung": "Entscheidungen",
    "befund": "Befunde",
    "wiederhole-nicht": "Wiederhole nicht",
    "offen": "Offene Punkte",
}
# Reihenfolge im Prompt: Warnungen zuerst, Journal zuletzt.
PROMPT_REIHENFOLGE = ("Wiederhole nicht", "Offene Punkte", "Entscheidungen", "Befunde", "Läufe")
MAX_TEXTLAENGE = 700
MAX_ZEICHEN_STANDARD = 6000
MAX_JE_ABSCHNITT_STANDARD = 25
KOPF = """# Projektgedächtnis: {projekt}

Dieses Gedächtnis gehört zum Projekt und wird von den Läufen selbst
fortgeschrieben. Der Workflow trägt jeden Lauf als Zeile unter "Läufe" ein;
alles andere ist bewusst knapp gehalten, damit es gelesen wird.

- **Wiederhole nicht**: was schon versucht wurde und nicht funktioniert hat.
- **Offene Punkte**: was ein Mensch entscheiden oder liefern muss.
- **Entscheidungen**: was gilt, damit es nicht erneut verhandelt wird.
- **Befunde**: belegte Erkenntnisse über das Zielprojekt.
"""


def slug_pruefen(slug: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", slug or ""):
        raise ValueError(f"Ungueltiger Projektname: {slug!r}")
    return slug


def pfad_fuer(wurzel: Path, slug: str) -> Path:
    return Path(wurzel) / "projects" / slug_pruefen(slug) / "GEDAEHNTNIS.md"


def parse(text: str) -> dict[str, list[str]]:
    """Liest die Abschnitte; alles ausserhalb bekannter Abschnitte wird verworfen."""
    abschnitte: dict[str, list[str]] = {name: [] for name in ABSCHNITTE}
    aktuell: str | None = None
    for rohzeile in text.splitlines():
        zeile = rohzeile.rstrip()
        if zeile.startswith("## "):
            name = zeile[3:].strip()
            aktuell = name if name in abschnitte else None
            continue
        if aktuell and zeile.startswith("- "):
            abschnitte[aktuell].append(zeile[2:].strip())
    return abschnitte


def render(projekt: str, abschnitte: dict[str, list[str]]) -> str:
    teile = [KOPF.format(projekt=projekt).rstrip(), ""]
    for name in ABSCHNITTE:
        eintraege = abschnitte.get(name, [])
        teile.append(f"## {name}")
        teile.append("")
        if eintraege:
            teile.extend(f"- {eintrag}" for eintrag in eintraege)
        else:
            teile.append("_(noch nichts eingetragen)_")
        teile.append("")
    return "\n".join(teile).rstrip() + "\n"


def lies(pfad: Path) -> dict[str, list[str]]:
    pfad = Path(pfad)
    if not pfad.is_file():
        return {name: [] for name in ABSCHNITTE}
    return parse(pfad.read_text(encoding="utf-8"))


def schreibe(pfad: Path, projekt: str, abschnitte: dict[str, list[str]]) -> None:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(render(projekt, abschnitte), encoding="utf-8")


def _normal(text: str) -> str:
    """Vergleichsform ohne Datum und Satzzeichen-Rauschen."""
    ohne_datum = re.sub(r"^\d{4}-\d{2}-\d{2}\s*\|?\s*", "", text.strip())
    return re.sub(r"\s+", " ", ohne_datum).strip().lower()


def eintrag(
    pfad: Path,
    projekt: str,
    art: str,
    text: str,
    datum: str | None = None,
    quelle: str | None = None,
) -> bool:
    """Haengt einen Eintrag an. Rueckgabe False, wenn er schon vorhanden war."""
    if art not in ARTEN:
        raise ValueError(f"Unbekannte Art: {art} (erlaubt: {', '.join(ARTEN)})")
    sauber = re.sub(r"\s+", " ", (text or "").strip())
    if not sauber:
        raise ValueError("Leerer Eintrag")
    if len(sauber) > MAX_TEXTLAENGE:
        sauber = sauber[: MAX_TEXTLAENGE - 1].rstrip() + "…"
    tag = datum or dt.date.today().isoformat()
    zeile = f"{tag} | {sauber}"
    if quelle:
        zeile += f" [{quelle}]"
    abschnitte = lies(pfad)
    vergleich = _normal(sauber)
    if any(_normal(vorhanden).startswith(vergleich) for vorhanden in abschnitte[ARTEN[art]]):
        return False
    abschnitte[ARTEN[art]].append(zeile)
    schreibe(pfad, projekt, abschnitte)
    return True


def kompakt(pfad: Path, projekt: str, max_je_abschnitt: int = MAX_JE_ABSCHNITT_STANDARD) -> int:
    """Behaelt je Abschnitt die neuesten Eintraege. Rueckgabe: entfernte Zeilen."""
    abschnitte = lies(pfad)
    entfernt = 0
    for name in ABSCHNITTE:
        eintraege = abschnitte[name]
        if len(eintraege) > max_je_abschnitt:
            entfernt += len(eintraege) - max_je_abschnitt
            abschnitte[name] = eintraege[-max_je_abschnitt:]
    if entfernt:
        schreibe(pfad, projekt, abschnitte)
    return entfernt


def laden(pfad: Path, max_zeichen: int = MAX_ZEICHEN_STANDARD) -> str:
    """Gekuerzter Block fuer den Prompt; leer, wenn nichts vermerkt ist."""
    abschnitte = lies(pfad)
    if not any(abschnitte.values()):
        return ""
    zeilen: list[str] = []
    verbraucht = 0
    gekuerzt = False
    for name in PROMPT_REIHENFOLGE:
        eintraege = abschnitte[name]
        if not eintraege:
            continue
        kopf = f"### {name}"
        if verbraucht + len(kopf) + 1 > max_zeichen:
            gekuerzt = True
            break
        zeilen.append(kopf)
        verbraucht += len(kopf) + 1
        for eintrag_text in reversed(eintraege):
            zeile = f"- {eintrag_text}"
            if verbraucht + len(zeile) + 1 > max_zeichen:
                gekuerzt = True
                break
            zeilen.append(zeile)
            verbraucht += len(zeile) + 1
        if gekuerzt:
            break
    if gekuerzt:
        zeilen.append("- … gekürzt, ältere Einträge weggelassen")
    return "\n".join(zeilen)


def status(pfad: Path) -> dict[str, int]:
    return {name: len(wert) for name, wert in lies(pfad).items()}


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Projektgedaechtnis der Devbox pflegen")
    parser.add_argument("--wurzel", default=str(Path(__file__).resolve().parents[1]))
    unter = parser.add_subparsers(dest="befehl", required=True)

    p_laden = unter.add_parser("laden", help="Block fuer den Prompt ausgeben")
    p_laden.add_argument("--projekt", required=True)
    p_laden.add_argument("--max-zeichen", type=int, default=MAX_ZEICHEN_STANDARD)

    p_eintrag = unter.add_parser("eintrag", help="Eintrag anhaengen")
    p_eintrag.add_argument("--projekt", required=True)
    p_eintrag.add_argument("--art", required=True, choices=sorted(ARTEN))
    p_eintrag.add_argument("--text", required=True)
    p_eintrag.add_argument("--datum", default=None)
    p_eintrag.add_argument("--quelle", default=None)

    p_kompakt = unter.add_parser("kompakt", help="Alte Eintraege entfernen")
    p_kompakt.add_argument("--projekt", required=True)
    p_kompakt.add_argument("--max", type=int, default=MAX_JE_ABSCHNITT_STANDARD)

    p_status = unter.add_parser("status", help="Anzahl Eintraege je Abschnitt")
    p_status.add_argument("--projekt", required=True)

    args = parser.parse_args(argv)
    wurzel = Path(args.wurzel)
    try:
        pfad = pfad_fuer(wurzel, args.projekt)
        if args.befehl == "laden":
            block = laden(pfad, args.max_zeichen)
            if block:
                print(block)
        elif args.befehl == "eintrag":
            neu = eintrag(pfad, args.projekt, args.art, args.text, args.datum, args.quelle)
            print("eingetragen" if neu else "schon vorhanden, uebersprungen")
        elif args.befehl == "kompakt":
            print(f"{kompakt(pfad, args.projekt, args.max)} Eintraege entfernt")
        elif args.befehl == "status":
            for name, anzahl in status(pfad).items():
                print(f"{name}: {anzahl}")
    except (ValueError, OSError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
