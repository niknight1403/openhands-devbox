"""Wachen fuer das Ablegen von Dateien, Fotos und Videos.

Der Weg vom Chat in den Draft-PR ist heikel: fremde Adressen, Groessen und
Dateitypen. Diese Tests halten die Grenzen fest, ohne ins Netz zu gehen; der
Testserver laeuft lokal.
"""

import http.server
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import assets  # noqa: E402

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000154a24f6d0000000049454e44ae426082"
)


class _Handler(http.server.BaseHTTPRequestHandler):
    antworten = {}

    def do_GET(self):  # noqa: N802 (http.server verlangt diesen Namen)
        typ, daten = self.antworten.get(self.path, ("text/plain", b"nicht da"))
        if self.path not in self.antworten:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *args):
        pass


class AssetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _Handler.antworten = {
            "/bild.png": ("image/png", PNG),
            "/seite.html": ("text/html; charset=utf-8", b"<html>nein</html>"),
            "/gross.bin": ("application/octet-stream", b"x" * 5000),
        }
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.faden = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.faden.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="assets-"))
        self.basis = f"http://127.0.0.1:{self.port}"

    def test_bild_wird_geladen_und_beschrieben(self):
        info = assets.holen(f"{self.basis}/bild.png", self.ordner, erlaube_privat=True)
        self.assertEqual(info["datei"], "bild.png")
        self.assertEqual(info["typ"], "image/png")
        self.assertTrue((self.ordner / "bild.png").is_file())
        self.assertEqual(len(info["sha256"]), 16)
        self.assertIn("bild.png", assets.markdown(info))

    def test_gleicher_name_weicht_aus(self):
        assets.holen(f"{self.basis}/bild.png", self.ordner, erlaube_privat=True)
        zweite = assets.holen(f"{self.basis}/bild.png", self.ordner, erlaube_privat=True)
        self.assertEqual(zweite["datei"], "bild-2.png")

    def test_webseite_statt_datei_wird_abgelehnt(self):
        with self.assertRaises(assets.AssetFehler):
            assets.holen(f"{self.basis}/seite.html", self.ordner, erlaube_privat=True)

    def test_groessengrenze_greift(self):
        with self.assertRaises(assets.AssetFehler):
            assets.holen(f"{self.basis}/gross.bin", self.ordner, max_mb=1, erlaube_privat=True)
        self.assertFalse(any(self.ordner.iterdir()))

    def test_unbekannter_dateityp_wird_abgelehnt(self):
        with self.assertRaises(assets.AssetFehler):
            assets.holen(f"{self.basis}/bild.png", self.ordner, name="schaedlich.exe", erlaube_privat=True)

    def test_lokale_adresse_ohne_freigabe_wird_abgelehnt(self):
        with self.assertRaises(assets.AssetFehler):
            assets.holen(f"{self.basis}/bild.png", self.ordner)

    def test_dateiname_wird_bereinigt(self):
        self.assertEqual(assets.name_bereinigen("../../etc/passwd"), "passwd")
        self.assertEqual(assets.name_bereinigen("Mein Foto (1).PNG"), "Mein-Foto-1-.PNG")
        self.assertEqual(assets.name_bereinigen(""), "datei")

    def test_liste_zeigt_abgelegte_dateien(self):
        assets.holen(f"{self.basis}/bild.png", self.ordner, erlaube_privat=True)
        eintraege = assets.liste(self.ordner)
        self.assertEqual([e["datei"] for e in eintraege], ["bild.png"])
        self.assertEqual(assets.liste(self.ordner / "gibtsnicht"), [])

    def test_groesse_wird_lesbar(self):
        self.assertEqual(assets.groesse_text(900), "900 B")
        self.assertEqual(assets.groesse_text(2048), "2 KB")
        self.assertEqual(assets.groesse_text(3 * 1048576), "3.0 MB")


if __name__ == "__main__":
    unittest.main()
