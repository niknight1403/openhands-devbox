"""Wachen fuer das Projektgedaechtnis.

Es muss nach jedem Lauf mehr wissen als vorher, ohne unbegrenzt zu wachsen und
ohne denselben Eintrag doppelt zu tragen.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import projekt_gedaechtnis as gedaechtnis  # noqa: E402


class GedaechtnisTest(unittest.TestCase):
    def setUp(self):
        self.wurzel = Path(tempfile.mkdtemp(prefix="gedaechtnis-"))
        self.pfad = gedaechtnis.pfad_fuer(self.wurzel, "testprojekt")

    def test_leeres_gedaechtnis_bleibt_leise(self):
        self.assertEqual(gedaechtnis.laden(self.pfad), "")
        self.assertEqual(set(gedaechtnis.status(self.pfad)), set(gedaechtnis.ABSCHNITTE))

    def test_eintrag_landet_im_richtigen_abschnitt(self):
        self.assertTrue(gedaechtnis.eintrag(self.pfad, "testprojekt", "entscheidung", "Squash statt Merge", datum="2026-11-09"))
        abschnitte = gedaechtnis.lies(self.pfad)
        self.assertEqual(abschnitte["Entscheidungen"], ["2026-11-09 | Squash statt Merge"])
        text = self.pfad.read_text(encoding="utf-8")
        self.assertIn("## Läufe", text)
        self.assertIn("_(noch nichts eingetragen)_", text)

    def test_derselbe_eintrag_kommt_nicht_zweimal(self):
        gedaechtnis.eintrag(self.pfad, "testprojekt", "befund", "Nur 14 Module ohne Test", datum="2026-11-09")
        self.assertFalse(gedaechtnis.eintrag(self.pfad, "testprojekt", "befund", "Nur 14 Module ohne Test", datum="2026-11-10"))

    def test_unbekannte_art_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            gedaechtnis.eintrag(self.pfad, "testprojekt", "quatsch", "text")

    def test_ungueltiger_projektname_wird_abgelehnt(self):
        for name in ["", "Gross", "../boese", "a"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                gedaechtnis.pfad_fuer(self.wurzel, name)

    def test_laden_zeigt_neueste_zuerst_und_warnungen_vorn(self):
        gedaechtnis.eintrag(self.pfad, "testprojekt", "lauf", "alt", datum="2026-11-01")
        gedaechtnis.eintrag(self.pfad, "testprojekt", "lauf", "neu", datum="2026-11-09")
        gedaechtnis.eintrag(self.pfad, "testprojekt", "wiederhole-nicht", "keyless Route pollinations", datum="2026-11-09")
        block = gedaechtnis.laden(self.pfad)
        self.assertLess(block.index("Wiederhole nicht"), block.index("### Läufe"))
        self.assertIn("2026-11-09 | neu", block)
        self.assertEqual(block.count("2026-11-09 | neu"), 1)

    def test_zeichenbudget_kappt_und_sagt_es(self):
        for nummer in range(40):
            gedaechtnis.eintrag(self.pfad, "testprojekt", "befund", f"Befund Nummer {nummer} mit etwas Text", datum="2026-11-09")
        block = gedaechtnis.laden(self.pfad, max_zeichen=300)
        self.assertLessEqual(len(block), 400)
        self.assertIn("gekürzt", block)

    def test_kompakt_behaelt_die_neuesten(self):
        for nummer in range(10):
            gedaechtnis.eintrag(self.pfad, "testprojekt", "lauf", f"Lauf {nummer}", datum="2026-11-09")
        entfernt = gedaechtnis.kompakt(self.pfad, "testprojekt", max_je_abschnitt=3)
        self.assertEqual(entfernt, 7)
        self.assertEqual(len(gedaechtnis.lies(self.pfad)["Läufe"]), 3)
        self.assertIn("Lauf 9", gedaechtnis.laden(self.pfad))

    def test_langer_text_wird_gekuerzt(self):
        gedaechtnis.eintrag(self.pfad, "testprojekt", "befund", "x" * 2000)
        eintrag = gedaechtnis.lies(self.pfad)["Befunde"][0]
        self.assertLessEqual(len(eintrag), gedaechtnis.MAX_TEXTLAENGE + len("2026-11-09 | ".replace("2026-11-09", "2026-11-09")))
        self.assertTrue(eintrag.endswith("…"))

    def test_cli_laden_und_status(self):
        gedaechtnis.eintrag(self.pfad, "testprojekt", "offen", "Entscheidung zu Neon-Theme fehlt", datum="2026-11-09")
        self.assertEqual(gedaechtnis._main(["--wurzel", str(self.wurzel), "status", "--projekt", "testprojekt"]), 0)
        self.assertEqual(gedaechtnis._main(["--wurzel", str(self.wurzel), "laden", "--projekt", "testprojekt"]), 0)
        self.assertEqual(gedaechtnis._main(["--wurzel", str(self.wurzel), "laden", "--projekt", "Boese!"]), 2)


if __name__ == "__main__":
    unittest.main()
