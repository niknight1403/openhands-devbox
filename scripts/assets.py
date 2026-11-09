"""Dateien, Fotos und Videos in einen Auftrag holen und im Projekt ablegen.

Der Workflow bekommt die Adressen als Eingabe, laedt sie hier herunter und legt
sie unter `docs/openhands/assets/` im Zielprojekt ab. Damit landen sie im
Draft-PR, sind fuer den Agenten lesbar und fuer den Menschen pruefbar.

Sicherheit: nur http und https, nur oeffentliche Adressen, harte Groessengrenze,
keine HTML-Seiten (sonst laedt man versehentlich eine Fehlerseite statt des
Bildes), Dateinamen werden bereinigt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from netzwerk import NetzFehler, laden  # noqa: E402

MAX_MB_STANDARD = 40
ERLAUBTE_ENDUNGEN = {
    "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic", "avif",
    "mp4", "webm", "mov", "m4v", "avi", "mkv",
    "pdf", "zip", "txt", "md", "csv", "json", "yaml", "yml", "log",
    "mp3", "wav", "m4a", "ogg",
}
ENDUNG_AUS_TYP = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "image/heic": "heic",
    "image/avif": "avif",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
    "application/pdf": "pdf",
    "application/zip": "zip",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/json": "json",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/mp4": "m4a",
    "audio/ogg": "ogg",
}


class AssetFehler(RuntimeError):
    """Datei wurde abgelehnt oder konnte nicht abgelegt werden."""


def name_bereinigen(name: str) -> str:
    """Nur harmlose Zeichen, keine Pfadanteile, begrenzte Laenge."""
    basis = Path(name).name
    basis = re.sub(r"[^A-Za-z0-9._-]+", "-", basis).strip("-._")
    basis = re.sub(r"-{2,}", "-", basis)
    if not basis:
        basis = "datei"
    if len(basis) > 80:
        stamm, punkt, endung = basis.rpartition(".")
        basis = (stamm[: 79 - len(endung)] + punkt + endung) if punkt else basis[:80]
    return basis


def groesse_text(bytes_anzahl: int) -> str:
    if bytes_anzahl < 1024:
        return f"{bytes_anzahl} B"
    if bytes_anzahl < 1048576:
        return f"{bytes_anzahl / 1024:.0f} KB"
    return f"{bytes_anzahl / 1048576:.1f} MB"


def holen(
    url: str,
    verzeichnis: Path,
    name: str | None = None,
    max_mb: int = MAX_MB_STANDARD,
    erlaube_privat: bool = False,
) -> dict:
    """Laedt eine Datei und legt sie im Zielverzeichnis ab."""
    try:
        daten, content_type, endgueltig = laden(
            url,
            max_bytes=max_mb * 1024 * 1024,
            erlaube_privat=erlaube_privat,
        )
    except NetzFehler as fehler:
        raise AssetFehler(str(fehler)) from fehler

    if content_type == "text/html":
        raise AssetFehler(
            "Die Adresse liefert eine Webseite statt einer Datei. "
            "Nutze die direkte Datei-Adresse (z. B. raw.githubusercontent.com)."
        )

    kandidat = name or Path(endgueltig.split("?")[0]).name
    dateiname = name_bereinigen(kandidat)
    if "." not in dateiname and content_type in ENDUNG_AUS_TYP:
        dateiname = f"{dateiname}.{ENDUNG_AUS_TYP[content_type]}"
    endung = dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
    if endung and endung not in ERLAUBTE_ENDUNGEN:
        raise AssetFehler(
            f"Dateityp .{endung} ist nicht vorgesehen (erlaubt: {', '.join(sorted(ERLAUBTE_ENDUNGEN))})"
        )

    ziel = Path(verzeichnis) / dateiname
    ziel.parent.mkdir(parents=True, exist_ok=True)
    lauf = 2
    while ziel.exists():
        stamm = dateiname.rsplit(".", 1)[0] if "." in dateiname else dateiname
        rest = "." + dateiname.rsplit(".", 1)[1] if "." in dateiname else ""
        ziel = Path(verzeichnis) / f"{stamm}-{lauf}{rest}"
        lauf += 1
    ziel.write_bytes(daten)

    return {
        "datei": ziel.name,
        "pfad": str(ziel),
        "bytes": len(daten),
        "groesse": groesse_text(len(daten)),
        "typ": content_type or mimetypes.guess_type(ziel.name)[0] or "unbekannt",
        "sha256": hashlib.sha256(daten).hexdigest()[:16],
        "quelle": endgueltig,
    }


def liste(verzeichnis: Path) -> list[dict]:
    verzeichnis = Path(verzeichnis)
    if not verzeichnis.is_dir():
        return []
    ergebnis = []
    for datei in sorted(verzeichnis.iterdir()):
        if datei.is_file() and not datei.name.startswith("."):
            ergebnis.append(
                {
                    "datei": datei.name,
                    "pfad": str(datei),
                    "bytes": datei.stat().st_size,
                    "groesse": groesse_text(datei.stat().st_size),
                    "typ": mimetypes.guess_type(datei.name)[0] or "unbekannt",
                }
            )
    return ergebnis


def markdown(info: dict | list[dict], praefix: str = "docs/openhands/assets") -> str:
    """Zeile(n) fuer den Prompt: was liegt wo, was ist es, wie gross."""
    eintraege = info if isinstance(info, list) else [info]
    zeilen = []
    for e in eintraege:
        zeilen.append(
            f"- `{praefix}/{e['datei']}` ({e['typ']}, {e['groesse']})"
            + (f", Quelle: {e['quelle']}" if e.get("quelle") else "")
        )
    return "\n".join(zeilen)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dateien in einen Auftrag holen")
    unter = parser.add_subparsers(dest="befehl", required=True)

    p_holen = unter.add_parser("holen", help="Datei von einer URL laden")
    p_holen.add_argument("--url", required=True)
    p_holen.add_argument("--verzeichnis", required=True)
    p_holen.add_argument("--name", default=None)
    p_holen.add_argument("--max-mb", type=int, default=MAX_MB_STANDARD)
    p_holen.add_argument("--erlaube-privat", action="store_true")
    p_holen.add_argument("--json", action="store_true")

    p_liste = unter.add_parser("liste", help="vorhandene Dateien zeigen")
    p_liste.add_argument("--verzeichnis", required=True)
    p_liste.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.befehl == "holen":
            info = holen(
                args.url,
                Path(args.verzeichnis),
                name=args.name,
                max_mb=args.max_mb,
                erlaube_privat=args.erlaube_privat,
            )
            print(json.dumps(info, ensure_ascii=False) if args.json else markdown(info))
        else:
            eintraege = liste(Path(args.verzeichnis))
            if args.json:
                print(json.dumps(eintraege, ensure_ascii=False, indent=2))
            elif eintraege:
                print(markdown(eintraege))
            else:
                print("keine Dateien vorhanden")
    except (AssetFehler, OSError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
