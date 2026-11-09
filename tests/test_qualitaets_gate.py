"""Wachen fuer das Qualitaets-Gate.

Das Gate darf nie den Lauf verhindern, muss aber ehrlich berichten: fehlende
Werkzeuge nennen, Befunde zeigen, ohne zu uebertreiben.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import qualitaets_gate as gate  # noqa: E402

WURZEL = Path(__file__).resolve().parents[1]


class GateTest(unittest.TestCase):
    def test_werkzeugliste_kennt_die_freien_werkzeuge(self):
        namen = {w.name for w in gate.werkzeuge(WURZEL)}
        for erwartet in {"pytest", "ruff", "bandit", "actionlint", "shellcheck", "kompilat"}:
            self.assertIn(erwartet, namen)

    def test_bericht_laeuft_und_nennt_fehlende_werkzeuge(self):
        daten = gate.bericht(WURZEL, ["pytest", "gibtsnicht"])
        self.assertIn("gibtsnicht", daten["fehlend"], "unbekannter Name muss gemeldet werden")
        if daten["werkzeuge"]:
            self.assertEqual(daten["werkzeuge"][0]["name"], "pytest")

    def test_kompilat_ist_immer_verfuegbar_und_sauber(self):
        daten = gate.bericht(WURZEL, ["kompilat"])
        self.assertTrue(daten["werkzeuge"], "kompilat muss laufen")
        self.assertEqual(daten["werkzeuge"][0]["status"], "sauber")

    def test_markdown_nennt_werkzeuge_und_befunde(self):
        daten = {
            "werkzeuge": [
                {"name": "ruff", "zweck": "Lint", "status": "befunde", "anzahl": 7,
                 "befunde": [f"scripts/x.py:1:1: F401 unused ({i})" for i in range(7)]},
                {"name": "pytest", "zweck": "Tests", "status": "sauber", "anzahl": 0, "befunde": []},
            ],
            "sauber": False,
            "fehlend": ["bandit"],
            "befunde_gesamt": 7,
        }
        text = gate.als_markdown(daten)
        self.assertIn("| ruff | Lint | Befunde | 7 |", text)
        self.assertIn("| pytest | Tests | sauber | 0 |", text)
        self.assertIn("weitere", text)
        self.assertIn("Nicht installiert: bandit", text)

    def test_markdown_ohne_werkzeuge_erklaert_sich(self):
        text = gate.als_markdown({"werkzeuge": [], "sauber": False, "fehlend": [], "befunde_gesamt": 0})
        self.assertIn("Kein Werkzeug gefunden", text)

    def test_streng_gibt_fehlerkennung_zurueck(self):
        # Ohne Befunde bleibt der Rueckgabewert 0, mit Befunden 1.
        sauber = {"werkzeuge": [], "sauber": True, "fehlend": [], "befunde_gesamt": 0}
        schmutzig = dict(sauber, sauber=False, befunde_gesamt=3)
        self.assertEqual(gate._main(["--nur", "kompilat"]), 0)
        self.assertEqual(gate.als_markdown(schmutzig).startswith("## Qualitäts-Gate"), True)
        self.assertFalse(sauber["sauber"] and schmutzig["sauber"])


if __name__ == "__main__":
    unittest.main()
