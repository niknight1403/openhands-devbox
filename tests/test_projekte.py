"""Wachen für die Projektablage in projects/.

Ein Projekt ist nur dann brauchbar, wenn Steckbrief und Prompt existieren, das
Zielrepository freigegeben ist und der Workflow den Auftrag wirklich einsetzt.
Diese Tests halten genau das fest, damit ein neues Projekt nicht halb angelegt
liegen bleibt.
"""

import subprocess
import unittest
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[1]
PROJEKTE = WURZEL / "projects"
TASK = WURZEL / ".github" / "workflows" / "openhands-task.yml"
AUTOPILOT = WURZEL / ".github" / "workflows" / "cybersarah-autopilot.yml"


def trigger(daten):
    """PyYAML liest das Schlüsselwort on als booleschen Wert True."""
    return daten[True] if True in daten else daten["on"]


def projekt_ordner():
    return sorted(p for p in PROJEKTE.iterdir() if p.is_dir() and (p / "project.env").is_file())


class ProjektAblageTest(unittest.TestCase):
    def test_jedes_projekt_hat_die_drei_dateien(self):
        ordner = projekt_ordner()
        self.assertTrue(ordner, "mindestens ein Projekt erwartet")
        for pfad in ordner:
            with self.subTest(projekt=pfad.name):
                self.assertRegex(pfad.name, r"^[a-z0-9][a-z0-9-]{1,40}$")
                self.assertTrue((pfad / "PROJECT.md").is_file(), "Steckbrief fehlt")
                self.assertTrue((pfad / "PROMPT.md").is_file(), "Prompt fehlt")

    def test_project_env_ist_sourcebar(self):
        for pfad in projekt_ordner():
            with self.subTest(projekt=pfad.name):
                ergebnis = subprocess.run(
                    ["bash", "-c", '. "$1"; printf "%s" "$TARGET_REPO_SLUG"', "_", str(pfad / "project.env")],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertTrue(ergebnis.stdout.strip(), "TARGET_REPO_SLUG ist leer")

    def test_zielrepository_ist_freigegeben(self):
        freigegeben = {
            zeile.strip()
            for zeile in (WURZEL / "config" / "targets.txt").read_text(encoding="utf-8").splitlines()
            if zeile.strip() and not zeile.strip().startswith("#")
        }
        for pfad in projekt_ordner():
            werte = dict(
                zeile.split("=", 1)
                for zeile in (pfad / "project.env").read_text(encoding="utf-8").splitlines()
                if "=" in zeile and not zeile.strip().startswith("#")
            )
            with self.subTest(projekt=pfad.name):
                self.assertIn(werte["TARGET_REPO_SLUG"].strip('"'), freigegeben)

    def test_prompt_traegt_phasen_und_grenzen(self):
        prompt = (PROJEKTE / "cybersarah-control-center" / "PROMPT.md").read_text(encoding="utf-8")
        for anker in (
            "docs/openhands/ANALYSE.md",
            "docs/openhands/STATUS.md",
            "Phase A: Analyse",
            "Phase B: Optimieren",
            "Phase C: Perfektionieren",
            "Draft-Pull-Request",
            ".github/workflows/",
        ):
            self.assertIn(anker, prompt)

    def test_steckbrief_nennt_kommandos_und_heikle_pfade(self):
        steckbrief = (PROJEKTE / "cybersarah-control-center" / "PROJECT.md").read_text(encoding="utf-8")
        for anker in ("npm run check", "npm run test", "drizzle/", "server/_core/"):
            self.assertIn(anker, steckbrief)


class WorkflowEinbindungTest(unittest.TestCase):
    def setUp(self):
        self.daten = yaml.safe_load(TASK.read_text(encoding="utf-8"))
        self.text = TASK.read_text(encoding="utf-8")

    def test_project_ist_eingabewert(self):
        self.assertIn("project", trigger(self.daten)["workflow_dispatch"]["inputs"])
        self.assertIn("project", trigger(self.daten)["workflow_call"]["inputs"])

    def test_projekt_wird_vor_dem_auschecken_geladen(self):
        laden = self.text.index("name: Projekt laden")
        auschecken = self.text.index("name: Zielprojekt auschecken")
        self.assertLess(laden, auschecken)

    def test_auschecken_nutzt_gepruefte_quelle(self):
        self.assertIn("repository: ${{ env.TARGET_REPO }}", self.text)
        self.assertNotIn("repository: niknight1403/${{ inputs.target", self.text)

    def test_whitelist_wird_erzwungen(self):
        self.assertIn('grep -Fxq "$ziel"', self.text)
        self.assertIn("config/targets.txt", self.text)

    def test_auftrag_haengt_projektprompt_an(self):
        self.assertIn("PROJECT_PROMPT_FILE", self.text)
        self.assertIn("--- Projektauftrag ---", self.text)
        self.assertIn("--- Projektkontext ---", self.text)

    def test_standardprofil_kommt_aus_dem_projekt(self):
        self.assertIn('PROFILE="${PROFILE_INPUT:-${DEFAULT_PROFILE:-superagent}}"', self.text)


class CyberSarahAutopilotTest(unittest.TestCase):
    def setUp(self):
        self.daten = yaml.safe_load(AUTOPILOT.read_text(encoding="utf-8"))
        self.job = self.daten["jobs"]["cybersarah"]

    def test_ruft_den_task_workflow_auf(self):
        self.assertEqual(self.job["uses"], "./.github/workflows/openhands-task.yml")
        self.assertEqual(self.job["secrets"], "inherit")
        self.assertEqual(self.job["with"]["project"], "cybersarah-control-center")

    def test_kadenz_passt_zum_projekt(self):
        env_datei = (PROJEKTE / "cybersarah-control-center" / "project.env").read_text(encoding="utf-8")
        cron_zeile = [z for z in env_datei.splitlines() if z.startswith("AUTOPILOT_CRON")][0]
        cron = cron_zeile.split("=", 1)[1].strip().strip('"')
        geplant = [eintrag["cron"] for eintrag in trigger(self.daten)["schedule"]]
        self.assertIn(cron, geplant)

    def test_rechte_erlauben_branch_und_draft_pr(self):
        rechte = self.daten["permissions"]
        self.assertEqual(rechte["contents"], "write")
        self.assertEqual(rechte["pull-requests"], "write")

    def test_kein_fester_client_run(self):
        # Ein fester Wert würde bei jedem Lauf denselben Branch treffen.
        self.assertNotIn("client_run", self.job["with"])


if __name__ == "__main__":
    unittest.main()
