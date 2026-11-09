"""Kostenlose Qualitaetswerkzeuge sammeln und als Bericht aufbereiten.

Das Gate prueft die Devbox selbst mit Werkzeugen, die ohne Lizenz und ohne
Schluessel laufen. Fehlt ein Werkzeug, ist das kein Fehler, sondern eine Zeile
im Bericht. Der Bericht geht als Markdown in die Lauf-Zusammenfassung, damit
Befunde sichtbar werden, ohne den Lauf zu blockieren; mit --streng bricht er ab.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
MAX_BEFUNDE_IM_BERICHT = 5


@dataclass
class Werkzeug:
    name: str
    zweck: str
    befehl: list[str]
    pflicht: bool = False
    befund_muster: list[str] = field(default_factory=list)
    modul: str | None = None

    def verfuegbar(self) -> bool:
        """Python-Module werden ueber den Import geprueft, alles andere per PATH."""
        if self.modul:
            return importlib.util.find_spec(self.modul) is not None
        return shutil.which(self.befehl[0]) is not None


def werkzeuge(wurzel: Path) -> list[Werkzeug]:
    python = sys.executable
    vorhandene = [
        Werkzeug("pytest", "Tests", [python, "-m", "pytest", "-q"], pflicht=True,
                 befund_muster=[r"^FAILED ", r"^ERROR ", r"\d+ failed"], modul="pytest"),
        Werkzeug("ruff", "Lint und Format", ["ruff", "check", "."],
                 befund_muster=[r"^[^ ]+\.py:\d+:\d+: "]),
        Werkzeug("bandit", "Sicherheit", ["bandit", "-q", "-r", "scripts"],
                 befund_muster=[r"^>> Issue: ", r"^\[.*\]\s+.*Severity"]),
        Werkzeug("actionlint", "Workflows", ["actionlint"],
                 befund_muster=[r"^\.github/workflows/"]),
        Werkzeug("shellcheck", "Shell-Skripte",
                 ["shellcheck", "-S", "warning", *[str(p) for p in sorted((wurzel / "scripts").glob("*.sh"))]],
                 befund_muster=[r"^In .* line \d+:", r"^.*\.sh:\d+:\d+: "]),
        Werkzeug("kompilat", "Syntax aller Python-Dateien",
                 [python, "-m", "compileall", "-q", "scripts", "tests"],
                 befund_muster=[r"^\*\*\*", r"SyntaxError"], modul="compileall"),
    ]
    return vorhandene


def _ausfuehren(werkzeug: Werkzeug, wurzel: Path) -> dict:
    try:
        ergebnis = subprocess.run(
            werkzeug.befehl,
            cwd=str(wurzel),
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as fehler:
        return {"name": werkzeug.name, "zweck": werkzeug.zweck, "status": "fehler",
                "rueckgabe": -1, "befunde": [], "hinweis": str(fehler)}
    ausgabe = (ergebnis.stdout or "") + (ergebnis.stderr or "")
    befunde = []
    for rohzeile in ausgabe.splitlines():
        zeile = rohzeile.strip()
        if zeile and any(re.search(muster, zeile) for muster in werkzeug.befund_muster):
            befunde.append(zeile[:200])
    status = "sauber" if ergebnis.returncode == 0 else "befunde"
    return {
        "name": werkzeug.name,
        "zweck": werkzeug.zweck,
        "status": status,
        "rueckgabe": ergebnis.returncode,
        "befunde": befunde[:50],
        "anzahl": len(befunde),
        "hinweis": _letzte_zeile(ausgabe),
    }


def _letzte_zeile(text: str) -> str:
    for zeile in reversed(text.strip().splitlines()):
        if zeile.strip():
            return zeile.strip()[:200]
    return ""


def bericht(wurzel: Path = WURZEL, namen: list[str] | None = None) -> dict:
    alle = werkzeuge(Path(wurzel))
    fehlend: list[str] = []
    if namen:
        gesucht = {n.lower() for n in namen}
        liste = [w for w in alle if w.name.lower() in gesucht]
        # Ein Tippfehler soll nicht stillschweigend verschwinden.
        fehlend.extend(sorted(gesucht - {w.name.lower() for w in alle}))
    else:
        liste = alle
    bereit = [w for w in liste if w.verfuegbar()]
    fehlend.extend(w.name for w in liste if w not in bereit)
    ergebnisse = [_ausfuehren(w, Path(wurzel)) for w in bereit]
    return {
        "werkzeuge": ergebnisse,
        "sauber": bool(ergebnisse) and all(e["status"] == "sauber" for e in ergebnisse),
        "fehlend": fehlend,
        "befunde_gesamt": sum(e.get("anzahl", 0) for e in ergebnisse),
    }


def als_markdown(daten: dict) -> str:
    zeilen = ["## Qualitäts-Gate", ""]
    if not daten["werkzeuge"]:
        zeilen.append("Kein Werkzeug gefunden. Installiere pytest, ruff, bandit, actionlint oder shellcheck.")
        return "\n".join(zeilen)
    zeilen.append("| Werkzeug | Zweck | Ergebnis | Befunde |")
    zeilen.append("| --- | --- | --- | --- |")
    for e in daten["werkzeuge"]:
        zeichen = "sauber" if e["status"] == "sauber" else ("Fehler" if e["status"] == "fehler" else "Befunde")
        zeilen.append(f"| {e['name']} | {e['zweck']} | {zeichen} | {e.get('anzahl', 0)} |")
    offene = [e for e in daten["werkzeuge"] if e.get("befunde")]
    if offene:
        zeilen.extend(["", "### Erste Befunde", ""])
        for e in offene:
            zeilen.append(f"**{e['name']}**")
            for befund in e["befunde"][:MAX_BEFUNDE_IM_BERICHT]:
                zeilen.append(f"- `{befund}`")
            if e.get("anzahl", 0) > MAX_BEFUNDE_IM_BERICHT:
                zeilen.append(f"- … {e['anzahl'] - MAX_BEFUNDE_IM_BERICHT} weitere")
            zeilen.append("")
    if daten.get("fehlend"):
        zeilen.append(f"Nicht installiert: {', '.join(daten['fehlend'])}")
    return "\n".join(zeilen).rstrip()


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freie Qualitaetswerkzeuge ausfuehren")
    parser.add_argument("--wurzel", default=str(WURZEL))
    parser.add_argument("--nur", default="", help="Komma-Liste von Werkzeugen")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown-datei", default=None)
    parser.add_argument("--streng", action="store_true", help="Rueckgabe 1 bei Befunden")
    args = parser.parse_args(argv)

    namen = [n.strip() for n in args.nur.split(",") if n.strip()] or None
    daten = bericht(Path(args.wurzel), namen)
    text = json.dumps(daten, ensure_ascii=False, indent=2) if args.json else als_markdown(daten)
    print(text)
    if args.markdown_datei:
        Path(args.markdown_datei).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown_datei).write_text(als_markdown(daten) + "\n", encoding="utf-8")
    if args.streng and not daten["sauber"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
