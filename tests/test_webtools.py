"""Wachen fuer die kostenlosen Web-Werkzeuge.

Seitentext und Trefferliste sind die einzigen zwei Faelle, die der Agent
braucht; beide werden hier ohne echtes Netz geprueft.
"""

import http.server
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import webtools  # noqa: E402

SEITE = b"""<html><head><title>T</title><style>body{color:red}</style></head>
<body><script>var geheim = 1;</script><h1>Ueberschrift</h1>
<p>Erster Absatz.</p><p>Zweiter Absatz.</p></body></html>"""

SUCHSEITE = b"""<html><body>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fa">Erster Titel</a>
<a class="result__snippet">Ein Ausschnitt zur ersten Quelle.</a>
<a class="result__a" href="https://example.net/b">Zweiter Titel</a>
<a class="result__snippet">Noch ein Ausschnitt.</a>
</body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/seite.html":
            daten, typ = SEITE, "text/html; charset=utf-8"
        elif self.path == "/text.txt":
            daten, typ = b"reiner Text ohne Markup", "text/plain; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *args):
        pass


class WebtoolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.faden = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.faden.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_html_zu_text_laesst_skripte_und_stile_weg(self):
        text = webtools.html_zu_text(SEITE.decode())
        self.assertIn("Ueberschrift", text)
        self.assertIn("Erster Absatz.", text)
        self.assertNotIn("geheim", text)
        self.assertNotIn("color:red", text)

    def test_seite_liefert_text_und_laenge(self):
        ergebnis = webtools.seite(f"http://127.0.0.1:{self.port}/seite.html", erlaube_privat=True)
        self.assertEqual(ergebnis["typ"], "text/html")
        self.assertIn("Zweiter Absatz.", ergebnis["text"])
        self.assertFalse(ergebnis["gekuerzt"])

    def test_seite_kuerzt_auf_budget(self):
        ergebnis = webtools.seite(f"http://127.0.0.1:{self.port}/seite.html", max_zeichen=10, erlaube_privat=True)
        self.assertTrue(ergebnis["gekuerzt"])
        self.assertLessEqual(len(ergebnis["text"]), 10)

    def test_reiner_text_bleibt_erhalten(self):
        ergebnis = webtools.seite(f"http://127.0.0.1:{self.port}/text.txt", erlaube_privat=True)
        self.assertEqual(ergebnis["text"], "reiner Text ohne Markup")

    def test_lokale_adresse_ohne_freigabe_wird_abgelehnt(self):
        with self.assertRaises(webtools.WebFehler):
            webtools.seite(f"http://127.0.0.1:{self.port}/seite.html")

    def test_suchseite_wird_ausgewertet(self):
        treffer = webtools._LINK.findall(SUCHSEITE.decode())
        self.assertEqual(len(treffer), 2)
        # Die Auswertung selbst braucht kein Netz: Muster und Bereinigung pruefen.
        saeuber = webtools._sauber("<b>Ein</b> Ausschnitt")
        self.assertEqual(saeuber, "Ein Ausschnitt")

    def test_leerer_suchbegriff_wird_abgelehnt(self):
        with self.assertRaises(webtools.WebFehler):
            webtools.suche("   ")


if __name__ == "__main__":
    unittest.main()
