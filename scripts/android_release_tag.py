#!/usr/bin/env python3
"""Validate Android release versions from GitHub events (stdlib only)."""
import json
import re
import sys
from pathlib import Path

VERSION = re.compile(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)-android\Z")
PREFIX = "release(android): "


def release_tag(event_name: str, ref: str, event_path: str, manual_tag: str = "") -> str:
    """Return a validated tag or raise ValueError; never interpret untrusted text as shell."""
    if event_name == "workflow_dispatch":
        tag = manual_tag
    elif event_name == "push" and ref.startswith("refs/tags/"):
        tag = ref.removeprefix("refs/tags/")
    elif event_name == "push" and ref == "refs/heads/main":
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        message = payload.get("head_commit", {}).get("message", "")
        first_line = message.splitlines()[0] if message else ""
        if not first_line.startswith(PREFIX):
            raise ValueError("main push is not an Android release commit")
        tag = first_line.removeprefix(PREFIX)
    else:
        raise ValueError("event is not allowed to publish Android releases")
    if not VERSION.fullmatch(tag):
        raise ValueError("release tag must match vMAJOR.MINOR.PATCH-android")
    return tag


if __name__ == "__main__":
    try:
        print(release_tag(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else ""))
    except (ValueError, OSError, json.JSONDecodeError, IndexError) as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
