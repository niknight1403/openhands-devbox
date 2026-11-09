"""Tests für die Auswertung der OpenHands-Ereignisse."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.openhands_events as ereignisse  # noqa: E402


def lege(verzeichnis: Path, name: str, inhalt: dict) -> Path:
    """Schreibt ein Ereignis in einen Gesprächsordner."""

    ordner = verzeichnis / name / "events"
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / f"{len(list(ordner.glob('*.json')))}.json"
    pfad.write_text(json.dumps(inhalt), encoding="utf-8")
    return pfad


class KlassifikationTest(unittest.TestCase):
    def test_kontingentfehler_ist_routenproblem(self):
        self.assertTrue(ereignisse.ist_routenproblem("Free limit reached: 1 reply every 45 seconds"))
        self.assertTrue(ereignisse.ist_routenproblem("litellm.RateLimitError: HTTP/1.1 429 Too Many Requests"))
        self.assertTrue(ereignisse.ist_routenproblem("model_not_found: gpt-9 gibt es nicht"))
        self.assertTrue(ereignisse.ist_routenproblem("RequestTimeout: timed out nach 30s"))

    def test_werkzeugfehler_ist_kein_routenproblem(self):
        self.assertFalse(ereignisse.ist_routenproblem("Datei README.md konnte nicht geschrieben werden"))
        self.assertFalse(ereignisse.ist_routenproblem("Der Agent hat den Plan nicht eingehalten"))

    def test_gemischte_fehler_brechen_ab(self):
        fehler = [("RateLimitError", "free limit reached"), ("ToolError", "Befehl fehlgeschlagen")]
        self.assertEqual(ereignisse.klassifiziere(fehler), 4)

    def test_nur_routenfehler_ergeben_code_drei(self):
        fehler = [("RateLimitError", "free limit reached"), ("APIError", "litellm.APIError")]
        self.assertEqual(ereignisse.klassifiziere(fehler), 3)

    def test_ohne_fehler_null(self):
        self.assertEqual(ereignisse.klassifiziere([]), 0)


class AuswertungTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.basis = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fremde_ereignisse_werden_ignoriert(self):
        lege(self.basis, "c1", {"kind": "ActionEvent", "action": "run"})
        lege(self.basis, "c1", {"kind": "ConversationErrorEvent", "code": "APIError", "detail": "HTTP/1.1 429"})
        self.assertEqual(len(ereignisse.sammle_fehler(self.basis)), 1)

    def test_tokens_werden_maskiert(self):
        lege(
            self.basis,
            "c1",
            {
                "kind": "ConversationErrorEvent",
                "code": "AuthenticationError",
                "detail": "ungültig: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345 und sk-abcdefghijklmnop",
            },
        )
        fehler = ereignisse.sammle_fehler(self.basis)
        text = fehler[0][1]
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345", text)
        self.assertNotIn("sk-abcdefghijklmnop", text)
        self.assertIn("<entfernt>", text)

    def test_kaputte_datei_wird_uebersprungen(self):
        ordner = self.basis / "c1" / "events"
        ordner.mkdir(parents=True)
        (ordner / "0.json").write_text("{kaputt", encoding="utf-8")
        self.assertEqual(ereignisse.sammle_fehler(self.basis), [])

    def test_nur_neue_gespraeche_zaehlen(self):
        lege(self.basis, "alt", {"kind": "ConversationErrorEvent", "code": "APIError", "detail": "429"})
        stand = self.basis / "stand.json"
        ereignisse.main(["--basis", str(self.basis), "--record", str(stand)])
        lege(self.basis, "neu", {"kind": "ConversationErrorEvent", "code": "APIError", "detail": "free limit reached"})
        ausgabe = io.StringIO()
        with redirect_stdout(ausgabe):
            code = ereignisse.main(["--basis", str(self.basis), "--since-state", str(stand)])
        self.assertEqual(code, 3)
        self.assertEqual(len(ereignisse.sammle_fehler(self.basis, {"alt"})), 1)

    def test_bericht_gibt_meldung_und_code(self):
        lege(self.basis, "c1", {"kind": "ConversationErrorEvent", "code": "APIError", "detail": "HTTP/1.1 503"})
        ausgabe = io.StringIO()
        with redirect_stdout(ausgabe):
            code = ereignisse.main(["--basis", str(self.basis)])
        self.assertEqual(code, 3)
        self.assertIn("Routenbezug", ausgabe.getvalue())
        self.assertIn("::error::OpenHands-Fehler APIError", ausgabe.getvalue())


if __name__ == "__main__":
    unittest.main()
