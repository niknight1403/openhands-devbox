from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-codespace.sh"


class BootstrapCodespaceTests(unittest.TestCase):
    def test_creates_private_key_once_and_starts_compose(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            bin_dir = root / "bin"
            scripts.mkdir()
            bin_dir.mkdir()
            script = scripts / "bootstrap-codespace.sh"
            shutil.copy2(SOURCE_SCRIPT, script)

            calls_file = root / "docker-calls.txt"
            docker = bin_dir / "docker"
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DOCKER_CALLS"\n')
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
            env["DOCKER_CALLS"] = str(calls_file)

            first = subprocess.run(
                ["bash", str(script)], cwd=root, env=env, check=True, text=True, capture_output=True
            )
            key_file = root / ".env"
            first_key = key_file.read_text().split("LOCAL_BACKEND_API_KEY=", 1)[1].strip()
            self.assertGreaterEqual(len(first_key), 40)
            self.assertEqual(stat.S_IMODE(key_file.stat().st_mode), 0o600)
            self.assertNotIn(first_key, first.stdout + first.stderr)

            subprocess.run(["bash", str(script)], cwd=root, env=env, check=True, text=True, capture_output=True)
            second_key = key_file.read_text().split("LOCAL_BACKEND_API_KEY=", 1)[1].strip()
            self.assertEqual(first_key, second_key)
            self.assertEqual(calls_file.read_text().splitlines(), ["compose up -d", "compose up -d"])

    def test_replaces_empty_key_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            bin_dir = root / "bin"
            scripts.mkdir()
            bin_dir.mkdir()
            script = scripts / "bootstrap-codespace.sh"
            shutil.copy2(SOURCE_SCRIPT, script)
            (root / ".env").write_text("OTHER=value\nLOCAL_BACKEND_API_KEY=\n")
            docker = bin_dir / "docker"
            docker.write_text("#!/bin/sh\nexit 0\n")
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

            subprocess.run(["bash", str(script)], cwd=root, env=env, check=True, capture_output=True)
            lines = (root / ".env").read_text().splitlines()
            keys = [line.split("=", 1)[1] for line in lines if line.startswith("LOCAL_BACKEND_API_KEY=")]
            self.assertEqual(len(keys), 1)
            self.assertTrue(keys[0])
            self.assertIn("OTHER=value", lines)


if __name__ == "__main__":
    unittest.main()
