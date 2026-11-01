from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "restore-protected-changes.py"


def run(*args: str, cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)
    return completed.stdout


def create_repo(root: Path) -> None:
    run("git", "init", "-q", cwd=root)
    run("git", "config", "user.email", "test@example.invalid", cwd=root)
    run("git", "config", "user.name", "Test", cwd=root)


class RestoreProtectedChangesTests(unittest.TestCase):
    def test_reverts_protected_tracked_changes_and_keeps_normal_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            create_repo(repo)
            (repo / ".github/workflows").mkdir(parents=True)
            (repo / ".github/workflows/ci.yml").write_text("safe: true\n")
            (repo / ".env.example").write_text("PLACEHOLDER=example\n")
            (repo / "app.py").write_text("safe = True\n")
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-qm", "initial", cwd=repo)

            (repo / ".github/workflows/ci.yml").write_text("unsafe: true\n")
            (repo / ".env.example").write_text("PLACEHOLDER=updated\n")
            (repo / "app.py").write_text("safe = False\n")
            (repo / ".github/workflows/new.yml").write_text("name: injected\n")

            run(sys.executable, str(SCRIPT), str(repo), cwd=repo)

            self.assertEqual((repo / ".github/workflows/ci.yml").read_text(), "safe: true\n")
            self.assertFalse((repo / ".github/workflows/new.yml").exists())
            self.assertEqual((repo / ".env.example").read_text(), "PLACEHOLDER=updated\n")
            self.assertEqual((repo / "app.py").read_text(), "safe = False\n")

    def test_removes_both_ends_of_rename_from_protected_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            create_repo(repo)
            (repo / ".github/workflows").mkdir(parents=True)
            source = repo / ".github/workflows/ci.yml"
            source.write_text("name: safe workflow\n")
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-qm", "initial", cwd=repo)

            run("git", "mv", ".github/workflows/ci.yml", "app.yml", cwd=repo)
            output = run(sys.executable, str(SCRIPT), str(repo), cwd=repo)

            self.assertIn("Protected change reverted: .github/workflows/ci.yml", output)
            self.assertTrue(source.exists())
            self.assertEqual(source.read_text(), "name: safe workflow\n")
            self.assertFalse((repo / "app.yml").exists())
            self.assertEqual(run("git", "status", "--porcelain", cwd=repo), "")

    def test_removes_copy_of_protected_file_under_neutral_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            create_repo(repo)
            (repo / "config").mkdir()
            protected = repo / "config/.env.production"
            protected.write_text("API_TOKEN=placeholder-secret-value\n")
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-qm", "initial", cwd=repo)

            (repo / "copied-config.txt").write_bytes(protected.read_bytes())
            output = run(sys.executable, str(SCRIPT), str(repo), cwd=repo)

            self.assertIn("Protected", output)
            self.assertFalse((repo / "copied-config.txt").exists())
            self.assertEqual(protected.read_text(), "API_TOKEN=placeholder-secret-value\n")
            self.assertEqual(run("git", "status", "--porcelain", cwd=repo), "")

    def test_removes_secret_value_copied_into_neutral_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            create_repo(repo)
            (repo / "config").mkdir()
            protected = repo / "config/.env.production"
            secret = "ghp_0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            protected.write_text(f"GITHUB_ACCESS_KEY={secret}\nOTHER=value\n")
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-qm", "initial", cwd=repo)

            (repo / "notes.md").write_text(f"debug output: {secret}\n")
            output = run(sys.executable, str(SCRIPT), str(repo), cwd=repo)

            self.assertNotIn(secret, output)
            self.assertFalse((repo / "notes.md").exists())
            self.assertEqual(protected.read_text(), f"GITHUB_ACCESS_KEY={secret}\nOTHER=value\n")
            self.assertEqual(run("git", "status", "--porcelain", cwd=repo), "")

    def test_keeps_documentation_with_long_public_endpoint_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            create_repo(repo)
            (repo / "config").mkdir()
            protected = repo / "config/.env.production"
            endpoint = "https://public.example.invalid/api/v1/very/long/public/path"
            protected.write_text(f"PUBLIC_ENDPOINT={endpoint}\n")
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-qm", "initial", cwd=repo)

            documentation = repo / "endpoint-docs.md"
            documentation.write_text(f"Public service endpoint: {endpoint}\n")
            run(sys.executable, str(SCRIPT), str(repo), cwd=repo)

            self.assertTrue(documentation.exists())
            self.assertIn(endpoint, documentation.read_text())
            self.assertEqual(protected.read_text(), f"PUBLIC_ENDPOINT={endpoint}\n")

    def test_reverts_env_and_private_key_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            create_repo(repo)
            (repo / "config").mkdir()
            (repo / "config/.env.production").write_text("TOKEN=placeholder\n")
            (repo / ".env.local").write_text("TOKEN=placeholder\n")
            (repo / "id_ed25519").write_text("placeholder\n")
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-qm", "initial", cwd=repo)

            (repo / ".env.local").write_text("TOKEN=changed\n")
            (repo / "config/.env.production").write_text("TOKEN=changed\n")
            (repo / "id_ed25519").write_text("changed\n")
            run(sys.executable, str(SCRIPT), str(repo), cwd=repo)

            self.assertEqual((repo / ".env.local").read_text(), "TOKEN=placeholder\n")
            self.assertEqual((repo / "config/.env.production").read_text(), "TOKEN=placeholder\n")
            self.assertEqual((repo / "id_ed25519").read_text(), "placeholder\n")


if __name__ == "__main__":
    unittest.main()
