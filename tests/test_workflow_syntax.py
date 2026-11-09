"""Wachen gegen kaputte Workflow-Schritte und Routenformate.

Beides hat schon Laeufe gekostet: ein nicht geschlossener Shell-Block in der
Lauf-Zusammenfassung (Exit 2) und ein Modellname mit Doppelpunkt, den der
Routen-Hunter als OpenRouter-Modell missverstand (HTTP 400).
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((WURZEL / ".github" / "workflows").glob("*.yml"))

sys.path.insert(0, str(WURZEL / "scripts"))

import free_route_hunter as hunter  # noqa: E402


def schritte(daten):
    for name, job in daten.get("jobs", {}).items():
        for schritt in job.get("steps", []):
            yield name, schritt


class ShellSyntaxTest(unittest.TestCase):
    def test_alle_schritte_sind_syntaktisch_gueltig(self):
        geprueft = 0
        for pfad in WORKFLOWS:
            daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
            for job, schritt in schritte(daten):
                run = schritt.get("run")
                if not run:
                    continue
                # GitHub-Ausdruecke werden erst zur Laufzeit ersetzt; bash -n
                # wuerde daran scheitern, nicht am Skript selbst.
                if "${{" in run:
                    continue
                with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as datei:
                    datei.write(run)
                    skript = datei.name
                ergebnis = subprocess.run(["bash", "-n", skript], capture_output=True, text=True)
                Path(skript).unlink()
                geprueft += 1
                with self.subTest(datei=pfad.name, schritt=schritt.get("name", job)):
                    self.assertEqual(ergebnis.returncode, 0, ergebnis.stderr.strip())
        self.assertGreater(geprueft, 10, "es sollten viele Schritte geprueft werden")

    def test_jede_shell_gruppe_wird_geschlossen(self):
        text = (WURZEL / ".github" / "workflows" / "openhands-task.yml").read_text(encoding="utf-8")
        geoeffnet = [z for z in text.splitlines() if z.strip() == "{"]
        geschlossen = [z for z in text.splitlines() if z.strip().startswith('} >> "')]
        self.assertEqual(len(geoeffnet), len(geschlossen), "offene Gruppe ohne Abschluss")
        self.assertTrue(any("GITHUB_STEP_SUMMARY" in z for z in geschlossen))


class RoutenformatTest(unittest.TestCase):
    def test_anbieter_mit_doppelpunkt_wird_erkannt(self):
        ziele = hunter.forced_candidates("cerebras:gpt-oss-120b")
        self.assertEqual([(z.provider, z.model) for z in ziele], [("cerebras", "gpt-oss-120b")])

    def test_schraegstrich_form_bleibt_unveraendert(self):
        ziele = hunter.forced_candidates("groq/llama-3.3-70b-versatile")
        self.assertEqual([(z.provider, z.model) for z in ziele], [("groq", "llama-3.3-70b-versatile")])

    def test_openrouter_modell_mit_doppelpunkt_bleibt_openrouter(self):
        ziele = hunter.forced_candidates("qwen/qwen3-coder:free")
        self.assertEqual([(z.provider, z.model) for z in ziele], [("openrouter", "qwen/qwen3-coder:free")])

    def test_modell_ohne_anbieter_geht_an_openrouter(self):
        ziele = hunter.forced_candidates("gpt-4o")
        self.assertEqual([(z.provider, z.model) for z in ziele], [("openrouter", "gpt-4o")])

    def test_leere_eingabe_ergibt_keine_vorgabe(self):
        self.assertEqual(hunter.forced_candidates("   "), [])


if __name__ == "__main__":
    unittest.main()
