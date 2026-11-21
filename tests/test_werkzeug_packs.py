"""Installation der lokalen Packs ohne Netzwerk und ohne Überschreiben."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import werkzeug_packs  # noqa: E402


class PackTests(unittest.TestCase):
    def test_installs_complete_skill_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            skill = source / "openhands-devbox-frontend-ux"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("skill", encoding="utf-8")
            (skill / "references" / "guide.md").write_text("guide", encoding="utf-8")
            target = root / "project"
            target.mkdir()
            result = werkzeug_packs.install("oberflaeche", target, source)
            installed = Path(result["target"]) / skill.name
            self.assertEqual((installed / "references" / "guide.md").read_text(), "guide")
            with self.assertRaisesRegex(ValueError, "bereits vorhanden"):
                werkzeug_packs.install("oberflaeche", target, source)
            skipped = werkzeug_packs.install("oberflaeche", target, source, skip_existing=True)
            self.assertEqual(skipped["skipped"], [skill.name])
            self.assertEqual((installed / "SKILL.md").read_text(), "skill")

    def test_rejects_symlink_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            source.mkdir()
            (source / "openhands-devbox-frontend-ux").symlink_to(root, target_is_directory=True)
            target = root / "target"
            target.mkdir()
            with self.assertRaisesRegex(ValueError, "Link"):
                werkzeug_packs.install("oberflaeche", target, source)
            self.assertFalse((target / ".agents").exists())


if __name__ == "__main__":
    unittest.main()
