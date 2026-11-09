"""Wachen für den Routenwechsel im Agentenlauf.

Die OpenHands-CLI endet bei Anbieterfehlern mit Exit 0. Ohne Auswertung der
Ereignisse merkt der Workflow den Ausfall erst am Ende und hat keinen
Ersatzversuch. Diese Tests halten den Auswertepfad fest.
"""

import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
TASK = WURZEL / ".github" / "workflows" / "openhands-task.yml"


class RoutenwechselTest(unittest.TestCase):
    def setUp(self):
        self.task = TASK.read_text(encoding="utf-8")
        self.agentenschritt = self.task.split("name: OpenHands-Superagent ausführen", 1)[1].split(
            "name: Geschützte Pfade wiederherstellen", 1
        )[0]

    def test_ereignisse_werden_je_versuch_ausgewertet(self):
        self.assertIn("--record", self.agentenschritt)
        self.assertIn("--since-state", self.agentenschritt)

    def test_routenfehler_loest_ersatzroute_aus(self):
        self.assertIn("HUNTER_EXCLUDE", self.agentenschritt)
        self.assertIn("Ersatzroute", self.agentenschritt)

    def test_fehler_ohne_routenbezug_bricht_sofort_ab(self):
        self.assertIn("ohne Routenbezug", self.agentenschritt)
        # Abbruch vor dem Ersatzversuch: der Hinweis steht im Rumpf der Rolle.
        self.assertLess(
            self.agentenschritt.index("ohne Routenbezug"),
            self.agentenschritt.index("Route ${LLM_ROUTE_NAME:-unbekannt} ausgefallen"),
        )

    def test_keine_globale_nachpruefung_alter_gespraeche(self):
        # Eine globale Prüfung würde Fehler bereits verworfener Routen erneut
        # melden und einen geretteten Lauf fälschlich rot machen.
        self.assertNotIn("import glob, json, re, sys", self.task)


if __name__ == "__main__":
    unittest.main()
