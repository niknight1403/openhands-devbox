"""Netzzugriffe der Devbox an einer Stelle: URL pruefen, begrenzt laden.

Alle Werkzeuge, die fremde Adressen holen (Dateien, Webseiten), gehen durch
diese Pruefung. So spricht ein Auftrag nicht versehentlich den Metadaten-
Endpunkt des Runners oder ein internes Netz an, und eine grosse Datei kann den
Lauf nicht auffressen.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
import urllib.request

ERLAUBTE_SCHEMATA = ("http", "https")
MAX_BYTES_STANDARD = 40 * 1024 * 1024
MAX_SEKUNDEN_STANDARD = 30
KOPFZEILEN = {
    "User-Agent": "openhands-devbox/1.0 (+https://github.com/niknight1403/openhands-devbox)",
    "Accept": "*/*",
}


class NetzFehler(RuntimeError):
    """Netzzugriff abgelehnt oder fehlgeschlagen."""


def _adressen(host: str) -> list[ipaddress._BaseAddress]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as fehler:
        raise NetzFehler(f"Host {host} ist nicht aufloesbar: {fehler}") from fehler
    gesehen = []
    for info in infos:
        rohadresse = info[4][0]
        try:
            adresse = ipaddress.ip_address(rohadresse)
        except ValueError:
            continue
        if adresse not in gesehen:
            gesehen.append(adresse)
    return gesehen


def ist_oeffentlich(adresse: ipaddress._BaseAddress) -> bool:
    return not (
        adresse.is_private
        or adresse.is_loopback
        or adresse.is_link_local
        or adresse.is_reserved
        or adresse.is_multicast
        or adresse.is_unspecified
    )


def pruefe_url(url: str, erlaube_privat: bool = False) -> str:
    """Gibt die bereinigte URL zurueck oder wirft NetzFehler."""
    bereinigt = (url or "").strip()
    if not bereinigt:
        raise NetzFehler("Leere Adresse")
    teile = urllib.parse.urlsplit(bereinigt)
    if teile.scheme.lower() not in ERLAUBTE_SCHEMATA:
        raise NetzFehler(f"Nur http und https sind erlaubt, nicht '{teile.scheme or 'ohne Schema'}'")
    host = teile.hostname
    if not host:
        raise NetzFehler("Adresse ohne Host")
    if not erlaube_privat:
        for adresse in _adressen(host):
            if not ist_oeffentlich(adresse):
                raise NetzFehler(f"Adresse {adresse} ist nicht oeffentlich")
    return bereinigt


def laden(
    url: str,
    max_bytes: int = MAX_BYTES_STANDARD,
    max_sekunden: int = MAX_SEKUNDEN_STANDARD,
    erlaube_privat: bool = False,
) -> tuple[bytes, str, str]:
    """Laedt eine Adresse und bricht ab, sobald max_bytes ueberschritten wird.

    Rueckgabe: (daten, content_type, endgueltige_url)
    """
    ziel = pruefe_url(url, erlaube_privat=erlaube_privat)
    anfrage = urllib.request.Request(ziel, headers=KOPFZEILEN)
    try:
        with urllib.request.urlopen(anfrage, timeout=max_sekunden) as antwort:  # nosec B310 - pruefe_url laesst nur http/https auf oeffentliche Adressen zu
            content_type = (antwort.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            gemeldet = antwort.headers.get("Content-Length")
            if gemeldet and gemeldet.isdigit() and int(gemeldet) > max_bytes:
                raise NetzFehler(
                    f"Datei ist mit {int(gemeldet) / 1048576:.1f} MB groesser als die Grenze von "
                    f"{max_bytes / 1048576:.1f} MB"
                )
            stuecke = []
            gesamt = 0
            while True:
                stueck = antwort.read(65536)
                if not stueck:
                    break
                gesamt += len(stueck)
                if gesamt > max_bytes:
                    raise NetzFehler(
                        f"Abbruch: mehr als {max_bytes / 1048576:.1f} MB geladen"
                    )
                stuecke.append(stueck)
            return b"".join(stuecke), content_type, antwort.geturl()
    except urllib.error.URLError as fehler:
        raise NetzFehler(f"Abruf fehlgeschlagen: {fehler.reason}") from fehler
    except urllib.error.HTTPError as fehler:
        raise NetzFehler(f"HTTP {fehler.code} bei {ziel}") from fehler
    except TimeoutError as fehler:
        raise NetzFehler(f"Zeitueberschreitung nach {max_sekunden}s bei {ziel}") from fehler
