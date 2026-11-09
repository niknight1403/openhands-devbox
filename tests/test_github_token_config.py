"""Wachen für den autonomen GitHub-Zugang der Devbox.

Der Agentenlauf darf ohne manuell angelegten Token schreiben können. Diese Tests
halten die Reihenfolge (eigener PAT, dann eingebauter GITHUB_TOKEN), die nötigen
Workflow-Rechte und die Regel fest, dass der Token den Agentenprozess nie erreicht.
"""

import re
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
TASK = WURZEL / ".github" / "workflows" / "openhands-task.yml"
CHECK = WURZEL / ".github" / "workflows" / "github-token-check.yml"


class GitHubZugangTest(unittest.TestCase):
    def setUp(self):
        self.task = TASK.read_text(encoding="utf-8")
        self.check = CHECK.read_text(encoding="utf-8")

    def test_workflow_hat_push_und_pr_rechte(self):
        self.assertIn("contents: write", self.task)
        self.assertIn("pull-requests: write", self.task)

    def test_pat_vor_eingebautem_token(self):
        pat = self.task.index('GH_TOKEN="${PAT:-}"')
        eingebaut = self.task.index('GH_TOKEN="${BUILTIN_TOKEN:-}"')
        self.assertLess(pat, eingebaut)

    def test_token_landet_nie_in_der_umgebung_des_agenten(self):
        for zeile in self.task.splitlines():
            if "GITHUB_ENV" in zeile and "GH_TOKEN=" in zeile:
                self.fail(f"Token darf nicht über GITHUB_ENV verteilt werden: {zeile.strip()}")

    def test_vorpruefung_prueft_mit_test_push(self):
        self.assertIn("name: GitHub-Zugang für Push und Draft-PR bestimmen", self.task)
        self.assertIn("Kein GitHub-Zugang mit Schreibrecht", self.task)
        self.assertIn("push --dry-run", self.task)
        self.assertIn("-c credential.helper=", self.task)

    def test_askpass_liest_den_token_aus_der_umgebung(self):
        # Die Hilfsdatei für den Test-Push darf keinen Tokenwert enthalten,
        # sondern nur den Namen der Umgebungsvariable.
        for inhalt in (self.task, self.check):
            passwort_zeilen = [z for z in inhalt.splitlines() if "*Password*" in z]
            self.assertTrue(passwort_zeilen, "Askpass-Zeile fehlt")
            for zeile in passwort_zeilen:
                # Nur eine Variable, nie ein Tokenwert.
                self.assertIn("$", zeile)
                self.assertNotRegex(zeile, r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]{10,}")

    def test_check_workflow_prueft_alle_freigegebenen_ziele(self):
        for repo in (
            "openhands-devbox",
            "Agenten-Villa",
            "LaunchpadControl",
            "CyberSarah-Control-Center",
            "Agentforge2",
            "AGI-Agenten",
        ):
            self.assertIn(repo, self.check)

    def test_workflows_enthalten_und_zeigen_keine_tokens(self):
        token_muster = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,})")
        for inhalt in (self.task, self.check):
            self.assertIsNone(token_muster.search(inhalt))
            self.assertNotIn('echo "$PAT"', inhalt)
            self.assertNotIn('echo "$BUILTIN_TOKEN"', inhalt)
            self.assertNotIn("set -x", inhalt)


if __name__ == "__main__":
    unittest.main()
