"""Wachen fuer die Verdrahtung: Gedaechtnis, Dateien und Qualitaets-Gate.

Ein Skript hilft nur, wenn der Workflow es wirklich aufruft. Diese Tests
pruefen die Kette vom Eingabefeld bis zum Prompt und zum Gedaechtnisschreiber.
"""

import sys
import unittest
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[1]
TASK = WURZEL / ".github" / "workflows" / "openhands-task.yml"
GATE = WURZEL / ".github" / "workflows" / "qualitaets-gate.yml"
PROJEKTE = WURZEL / "projects"

sys.path.insert(0, str(WURZEL / "scripts"))

import projekt_gedaechtnis as gedaechtnis  # noqa: E402


def lade(pfad):
    return yaml.safe_load(pfad.read_text(encoding="utf-8"))


def trigger(daten):
    return daten[True] if True in daten else daten["on"]


class WorkflowVerdrahtungTest(unittest.TestCase):
    def setUp(self):
        self.workflow = lade(TASK)
        self.schritte = self.workflow["jobs"]["openhands"]["steps"]

    def test_assets_eingabe_in_beiden_startwegen(self):
        eingaben = trigger(self.workflow)
        self.assertIn("assets", eingaben["workflow_dispatch"]["inputs"])
        self.assertIn("assets", eingaben["workflow_call"]["inputs"])

    def test_gedaechtnis_wird_geladen_und_geschrieben(self):
        namen = [s.get("name", "") for s in self.schritte]
        self.assertTrue(any("Projektgedächtnis und Dateien laden" == n for n in namen))
        schreiber = [s for s in self.schritte if s.get("name") == "Projektgedächtnis fortschreiben"]
        self.assertEqual(len(schreiber), 1)
        self.assertIn("always()", schreiber[0]["if"])
        self.assertIn("projekt_gedaechtnis.py", schreiber[0]["run"])
        self.assertIn("api.github.com", schreiber[0]["run"])

    def test_auftrag_enthaelt_gedaechtnis_und_dateien(self):
        schritt = next(s for s in self.schritte if s.get("name") == "Aufgabe und Profil vorbereiten")
        self.assertIn("Projektgedächtnis aus früheren Läufen", schritt["run"])
        self.assertIn("Mitgelieferte Dateien", schritt["run"])
        self.assertIn("GEDAECHTNIS_DATEI", schritt["run"])

    def test_dateilader_nutzt_das_asset_skript_und_meldet_anzahl(self):
        schritt = next(s for s in self.schritte if s.get("name") == "Projektgedächtnis und Dateien laden")
        self.assertIn("assets.py holen", schritt["run"])
        self.assertIn('docs/openhands/assets', schritt["run"])
        self.assertIn("ASSETS_ANZAHL", schritt["run"])

    def test_projekt_laden_gibt_gedaechtnispfad_weiter(self):
        schritt = next(s for s in self.schritte if s.get("name") == "Projekt laden")
        self.assertIn("PROJECT_MEMORY_FILE", schritt["run"])
        self.assertIn("GEDAEHNTNIS.md", schritt["run"])


class QualitaetsGateWorkflowTest(unittest.TestCase):
    def test_gate_laeuft_bei_push_und_zeitplan(self):
        daten = lade(GATE)
        ausloeser = trigger(daten)
        self.assertIn("push", ausloeser)
        self.assertIn("schedule", ausloeser)
        self.assertIn("workflow_dispatch", ausloeser)

    def test_gate_ruft_das_skript_auf_und_legt_bericht_ab(self):
        daten = lade(GATE)
        schritte = daten["jobs"]["gate"]["steps"]
        zusammen = "\n".join(s.get("run", "") for s in schritte)
        self.assertIn("qualitaets_gate.py", zusammen)
        self.assertIn("requirements-dev.txt", zusammen)
        artefakt = [s for s in schritte if s.get("uses", "").startswith("actions/upload-artifact")]
        self.assertTrue(artefakt, "Bericht muss als Artefakt abgelegt werden")


class GedaechtnisdateienTest(unittest.TestCase):
    def test_vorhandene_gedaechtnisse_sind_lesbar(self):
        dateien = sorted(PROJEKTE.glob("*/GEDAEHNTNIS.md"))
        self.assertTrue(dateien, "mindestens ein Projektgedaechtnis erwartet")
        for pfad in dateien:
            with self.subTest(datei=pfad.name):
                abschnitte = gedaechtnis.lies(pfad)
                self.assertEqual(set(abschnitte), set(gedaechtnis.ABSCHNITTE))
                block = gedaechtnis.laden(pfad)
                self.assertTrue(block, "Gedaechtnis darf nicht leer sein")

    def test_cybersarah_kennt_den_naechsten_schritt(self):
        pfad = PROJEKTE / "cybersarah-control-center" / "GEDAEHNTNIS.md"
        self.assertTrue(pfad.is_file())
        abschnitte = gedaechtnis.lies(pfad)
        self.assertTrue(abschnitte["Läufe"], "Läufe fehlen")
        self.assertTrue(abschnitte["Offene Punkte"], "offene Punkte fehlen")
        self.assertIn("Befund 3", gedaechtnis.laden(pfad))

    def test_prompt_verweist_auf_gedaechtnis_und_dateien(self):
        text = (PROJEKTE / "cybersarah-control-center" / "PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("Projektgedächtnis aus früheren", text)
        self.assertIn("docs/openhands/assets/", text)


if __name__ == "__main__":
    unittest.main()
