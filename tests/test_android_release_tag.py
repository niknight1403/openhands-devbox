"""Ten release-gate regression scenarios; no network or credentials needed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from android_release_tag import release_tag


class AndroidReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.event = Path(self.tmp.name) / "event.json"

    def push(self, message):
        self.event.write_text(json.dumps({"head_commit": {"message": message}}), encoding="utf-8")
        return release_tag("push", "refs/heads/main", str(self.event))

    def test_sprint_01_main_release_commit(self):
        self.assertEqual(self.push("release(android): v1.3.0-android"), "v1.3.0-android")

    def test_sprint_02_multiline_commit_message(self):
        self.assertEqual(self.push("release(android): v2.0.1-android\n\nRelease notes"), "v2.0.1-android")

    def test_sprint_03_manual_dispatch(self):
        self.assertEqual(release_tag("workflow_dispatch", "refs/heads/main", "", "v3.2.1-android"), "v3.2.1-android")

    def test_sprint_04_tag_push(self):
        self.assertEqual(release_tag("push", "refs/tags/v4.0.0-android", ""), "v4.0.0-android")

    def test_sprint_05_reject_non_release_main_commit(self):
        with self.assertRaises(ValueError):
            self.push("fix: unrelated change")

    def test_sprint_06_reject_pr_release(self):
        with self.assertRaises(ValueError):
            release_tag("pull_request", "refs/pull/1/merge", "", "v1.3.0-android")

    def test_sprint_07_reject_other_branch(self):
        with self.assertRaises(ValueError):
            release_tag("push", "refs/heads/agent/test", "", "v1.3.0-android")

    def test_sprint_08_reject_injection(self):
        with self.assertRaises(ValueError):
            self.push("release(android): v1.3.0-android; echo unsafe")

    def test_sprint_09_reject_invalid_version(self):
        with self.assertRaises(ValueError):
            self.push("release(android): v1.3-android")

    def test_sprint_10_reject_missing_payload(self):
        self.event.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            release_tag("push", "refs/heads/main", str(self.event))


if __name__ == "__main__":
    unittest.main()
