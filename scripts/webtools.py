"""Kostenlose Web-Werkzeuge fuer Agentenlaeufe: Seite lesen, Web suchen.

Beides ohne Schluessel und ohne Zusatzpakete, damit es auf jedem Runner
funktioniert. Bewusst schmal: Text einer Seite, Trefferliste einer Suche. Wer
mehr braucht, nimmt curl oder die OpenHands-Werkzeuge.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from netzwerk import NetzFehler, laden  # noqa: E402

MAX_ZEICHEN_STANDARD = 8000
SUCHE_URL = "https://html.duckduckgo.com/html/?q="


class WebFehler(RuntimeError):
    """Abruf oder Auswertung fehlgeschlagen."""


class _TextSammler(HTMLParser):
    """Holt sichtbaren Text; Script, Style und Navigation bleiben aussen vor."""

    IGNORIEREN = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stuecke: list[str] = []
        self._tiefe = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.IGNORIEREN:
            self._tiefe += 1
        elif tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"} and not self._tiefe:
            self.stuecke.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORIEREN and self._tiefe:
            self._tiefe -= 1

    def handle_data(self, daten: str) -> None:
        if not self._tiefe:
            self.stuecke.append(daten)

    @property
    def text(self) -> str:
        roh = "".join(self.stuecke)
        zeilen = [re.sub(r"[ \t]+", " ", z).strip() for z in roh.splitlines()]
        return "\n".join(z for z in zeilen if z)


def html_zu_text(html: str) -> str:
    sammler = _TextSammler()
    sammler.feed(html)
    sammler.close()
    return sammler.text


def seite(url: str, max_zeichen: int = MAX_ZEICHEN_STANDARD, erlaube_privat: bool = False) -> dict:
    try:
        daten, content_type, endgueltig = laden(url, max_bytes=8 * 1024 * 1024, erlaube_privat=erlaube_privat)
    except NetzFehler as fehler:
        raise WebFehler(str(fehler)) from fehler
    zeichensatz = "utf-8"
    if "charset=" in content_type:
        zeichensatz = content_type.split("charset=")[-1].strip() or "utf-8"
    try:
        roh = daten.decode(zeichensatz, errors="replace")
    except LookupError:
        roh = daten.decode("utf-8", errors="replace")
    text = html_zu_text(roh) if "html" in content_type or roh.lstrip().startswith("<") else roh
    gekuerzt = len(text) > max_zeichen
    return {
        "url": endgueltig,
        "typ": content_type or "unbekannt",
        "zeichen": len(text),
        "gekuerzt": gekuerzt,
        "text": text[:max_zeichen],
    }


_LINK = re.compile(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_TREFFER = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def _sauber(html: str) -> str:
    return re.sub(r"\s+", " ", _TAGS.sub("", html)).strip()


def suche(begriff: str, max_treffer: int = 5, erlaube_privat: bool = False) -> list[dict]:
    if not begriff.strip():
        raise WebFehler("Leerer Suchbegriff")
    url = SUCHE_URL + urllib.parse.quote_plus(begriff.strip())
    try:
        daten, _, _ = laden(url, max_bytes=4 * 1024 * 1024, erlaube_privat=erlaube_privat)
    except NetzFehler as fehler:
        raise WebFehler(str(fehler)) from fehler
    html = daten.decode("utf-8", errors="replace")
    ausschnitte = _TREFFER.findall(html)
    treffer = []
    for index, (href, titel) in enumerate(_LINK.findall(html)[:max_treffer]):
        ziel = urllib.parse.unquote(href)
        # DuckDuckGo verpackt Ziele in /l/?uddg=<ziel>
        if "uddg=" in ziel:
            ziel = urllib.parse.unquote(ziel.split("uddg=", 1)[1].split("&", 1)[0])
        treffer.append(
            {
                "titel": _sauber(titel),
                "url": ziel,
                "ausschnitt": _sauber(ausschnitte[index]) if index < len(ausschnitte) else "",
            }
        )
    return treffer


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kostenlose Web-Werkzeuge")
    unter = parser.add_subparsers(dest="befehl", required=True)

    p_seite = unter.add_parser("seite", help="Seitentext lesen")
    p_seite.add_argument("--url", required=True)
    p_seite.add_argument("--max-zeichen", type=int, default=MAX_ZEICHEN_STANDARD)
    p_seite.add_argument("--erlaube-privat", action="store_true")

    p_suche = unter.add_parser("suche", help="Web durchsuchen")
    p_suche.add_argument("--begriff", required=True)
    p_suche.add_argument("--max-treffer", type=int, default=5)
    p_suche.add_argument("--erlaube-privat", action="store_true")
    p_suche.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.befehl == "seite":
            ergebnis = seite(args.url, args.max_zeichen, args.erlaube_privat)
            print(f"# {ergebnis['url']} ({ergebnis['typ']}, {ergebnis['zeichen']} Zeichen)")
            print(ergebnis["text"])
        else:
            treffer = suche(args.begriff, args.max_treffer, args.erlaube_privat)
            if args.json:
                print(json.dumps(treffer, ensure_ascii=False, indent=2))
            else:
                for nummer, t in enumerate(treffer, 1):
                    print(f"{nummer}. {t['titel']}\n   {t['url']}\n   {t['ausschnitt']}")
                if not treffer:
                    print("keine Treffer")
    except WebFehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
