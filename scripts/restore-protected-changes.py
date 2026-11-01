#!/usr/bin/env python3
"""Revert protected paths and detected copies of protected credential content."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ALLOWED_ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
PROTECTED_SUFFIXES = {".pem", ".p12", ".pfx", ".key"}
PROTECTED_NAMES = {"id_rsa", "id_ed25519", "credentials.json"}
SECRET_FIELD_MARKERS = ("token", "secret", "password", "credential", "private", "api_key", "apikey", "key")
MAX_SCAN_BYTES = 10 * 1024 * 1024


def git_bytes(root: Path, *args: str) -> list[bytes]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [item for item in result.stdout.split(b"\0") if item]


def changed_path_groups(root: Path) -> list[tuple[str, tuple[bytes, ...]]]:
    """Parse NUL-delimited diff status records, retaining both ends of renames/copies."""
    fields = git_bytes(
        root,
        "diff",
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies-harder",
        "HEAD",
    )
    groups: list[tuple[str, tuple[bytes, ...]]] = []
    index = 0
    while index < len(fields):
        status = fields[index].decode("ascii", errors="replace")
        index += 1
        path_count = 2 if status.startswith(("R", "C")) else 1
        paths = tuple(fields[index : index + path_count])
        if len(paths) != path_count:
            raise ValueError(f"Incomplete Git diff record for status {status!r}")
        groups.append((status, paths))
        index += path_count
    return groups


def is_protected(raw_path: bytes) -> bool:
    path = Path(os.fsdecode(raw_path).replace("\\", "/"))
    value = path.as_posix()
    name = path.name.lower()

    if value == ".github/workflows" or value.startswith(".github/workflows/"):
        return True
    if name == ".env" or (name.startswith(".env.") and name not in ALLOWED_ENV_TEMPLATES):
        return True
    if name in PROTECTED_NAMES or path.suffix.lower() in PROTECTED_SUFFIXES:
        return True
    return False


def is_credential_file(raw_path: bytes) -> bool:
    path = Path(os.fsdecode(raw_path).replace("\\", "/"))
    return is_protected(raw_path) and (
        path.name.lower().startswith(".env")
        or path.name.lower() in PROTECTED_NAMES
        or path.suffix.lower() in PROTECTED_SUFFIXES
    )


def extract_credential_tokens(raw_path: bytes, content: bytes) -> set[bytes]:
    """Extract candidate secret values without ever printing them."""
    path = Path(os.fsdecode(raw_path).replace("\\", "/"))
    name = path.name.lower()
    tokens: set[bytes] = set()
    stripped = content.strip()
    if len(stripped) >= 16:
        tokens.add(stripped)

    if name.startswith(".env"):
        for line in content.splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.startswith(b"#") or b"=" not in cleaned:
                continue
            key, value = cleaned.split(b"=", 1)
            key_text = key.decode("utf-8", errors="ignore").lower()
            value = value.strip().strip(b"\"'")
            if len(value) >= 8 and any(marker in key_text for marker in SECRET_FIELD_MARKERS):
                tokens.add(value)

    if name == "credentials.json":
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None

        def collect(value: object, key: str = "") -> None:
            if isinstance(value, dict):
                for child_key, child in value.items():
                    collect(child, str(child_key).lower())
            elif isinstance(value, list):
                for child in value:
                    collect(child, key)
            elif isinstance(value, str):
                encoded = value.encode("utf-8")
                if len(encoded) >= 8 and any(marker in key for marker in SECRET_FIELD_MARKERS):
                    tokens.add(encoded)

        if parsed is not None:
            collect(parsed)

    if path.suffix.lower() in PROTECTED_SUFFIXES or name in {"id_rsa", "id_ed25519"}:
        for line in content.splitlines():
            line = line.strip()
            if len(line) >= 24:
                tokens.add(line)

    return {token for token in tokens if len(token) >= 8}


def protected_tokens_from_head(root: Path, head_paths: set[bytes]) -> set[bytes]:
    tokens: set[bytes] = set()
    for raw_path in head_paths:
        if not is_credential_file(raw_path):
            continue
        spec = "HEAD:" + os.fsdecode(raw_path)
        result = subprocess.run(
            ["git", "-C", str(root), "show", spec],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            tokens.update(extract_credential_tokens(raw_path, result.stdout))
    return tokens


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: restore-protected-changes.py <workspace>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    if not (root / ".git").exists():
        print(f"Not a Git workspace: {root}", file=sys.stderr)
        return 2

    # Register new files as intent-to-add so Git can detect copies from unchanged files.
    # This records no file contents; ordinary additions remain for the later PR step.
    subprocess.run(["git", "-C", str(root), "add", "--intent-to-add", "--all"], check=True)

    groups = changed_path_groups(root)
    protected_paths: set[bytes] = set()
    changed_paths: set[bytes] = set()
    for _status, paths in groups:
        changed_paths.update(paths)
        # If either end of a rename/copy is protected, revert/remove both ends.
        if any(is_protected(path) for path in paths):
            protected_paths.update(paths)

    head_paths = set(git_bytes(root, "ls-tree", "-r", "--name-only", "-z", "HEAD"))
    index_paths = set(git_bytes(root, "ls-files", "-z"))
    untracked_paths = set(git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z"))
    protected_paths.update(path for path in untracked_paths if is_protected(path))

    # Detect a protected secret copied as a value/snippet into a neutral filename.
    secret_tokens = protected_tokens_from_head(root, head_paths)
    if secret_tokens:
        for raw_path in changed_paths | set(untracked_paths):
            if raw_path in head_paths or is_protected(raw_path):
                continue
            path = root / os.fsdecode(raw_path)
            if path.is_symlink() or not path.is_file():
                continue
            try:
                if path.stat().st_size > MAX_SCAN_BYTES:
                    continue
                content = path.read_bytes()
            except OSError:
                continue
            if any(token in content for token in secret_tokens):
                protected_paths.add(raw_path)
                print(f"::warning::Protected credential content found and removed from: {path.relative_to(root)}")

    for raw_path in sorted(protected_paths):
        path = os.fsdecode(raw_path)
        if raw_path in head_paths:
            subprocess.run(
                ["git", "-C", str(root), "restore", "--source=HEAD", "--staged", "--worktree", "--", path],
                check=True,
            )
            print(f"::warning::Protected change reverted: {path}")
        elif raw_path in index_paths:
            subprocess.run(["git", "-C", str(root), "rm", "-f", "--", path], check=True)
            print(f"::warning::Protected added/copied path removed: {path}")
        else:
            subprocess.run(["git", "-C", str(root), "clean", "-fd", "--", path], check=True)
            print(f"::warning::Protected untracked path removed: {path}")

    if not protected_paths:
        print("No protected workflow or credential paths were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
