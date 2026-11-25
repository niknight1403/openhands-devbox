"""Installiert kuratierte, lokal versionierte Entwickler-Packs in ein Zielprojekt."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agents" / "skills"
PACKS = {
    "entwicklung": ("openhands-devbox-autonomous-development", "openhands-devbox-automated-refactoring"),
    "qualitaet": ("openhands-devbox-quality-engineering", "openhands-devbox-security"),
    "oberflaeche": ("openhands-devbox-frontend-ux",),
    "integrationen": ("openhands-devbox-integrations",),
}


def select_packs(task: str, profile: str = "superagent") -> tuple[str, ...]:
    """Deterministic selection from the local allowlist; no external installation."""
    if profile == "swarm":
        return tuple(PACKS)
    selected = {"entwicklung", "qualitaet"}
    normalized = task.casefold()
    if profile == "frontend" or any(word in normalized for word in (
        "frontend", "design", "android", "compose", "oberfläche", "ui", "ux", "layout"
    )):
        selected.add("oberflaeche")
    if any(word in normalized for word in (
        "api", "mcp", "connector", "integration", "llm", "routing", "werkzeug", "plugin"
    )):
        selected.add("integrationen")
    return tuple(pack for pack in PACKS if pack in selected)


def install(pack: str, target: Path, source: Path = SOURCE, skip_existing: bool = False) -> dict:
    """Kopiert ausschließlich geprüfte lokale Skills; vorhandene bleiben unangetastet."""
    if pack not in PACKS:
        raise ValueError(f"Unbekanntes Pack: {pack}. Verfügbar: {', '.join(PACKS)}")
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f"Zielprojekt existiert nicht: {target}")
    destination = target / ".agents" / "skills"
    selected = PACKS[pack]
    if (target / ".agents").is_symlink() or destination.is_symlink():
        raise ValueError("Zielverzeichnis ist ein Link")
    skipped = []
    for name in selected:
        skill = source / name
        if skill.is_symlink() or not skill.is_dir() or not (skill / "SKILL.md").is_file():
            raise ValueError(f"Skill fehlt oder ist ein Link: {name}")
        if any(path.is_symlink() for path in skill.rglob("*")):
            raise ValueError(f"Skill enthält einen Link: {name}")
        if (destination / name).exists() or (destination / name).is_symlink():
            if not skip_existing or (destination / name).is_symlink():
                raise ValueError(f"Skill ist im Ziel bereits vorhanden: {name}")
            skipped.append(name)
    installed = []
    try:
        destination.mkdir(parents=True, exist_ok=True)
        for name in selected:
            if name in skipped:
                continue
            shutil.copytree(source / name, destination / name, symlinks=False)
            installed.append(name)
    except OSError:
        for name in installed:
            shutil.rmtree(destination / name)
        raise
    return {"pack": pack, "installed": installed, "skipped": skipped, "target": str(destination)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Verfügbare Packs zeigen")
    parser.add_argument("--pack", choices=PACKS)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--skip-existing", action="store_true", help="Vorhandene Skills im Ziel erhalten")
    parser.add_argument("--auto", action="store_true", help="Packs anhand des Auftrags auswählen")
    parser.add_argument("--task", default="")
    parser.add_argument("--profile", default="superagent")
    args = parser.parse_args()
    if args.list:
        print(json.dumps(PACKS, ensure_ascii=False, indent=2))
        return 0
    if args.auto:
        if not args.target or args.pack:
            parser.error("--auto benötigt --target und darf nicht mit --pack kombiniert werden")
        try:
            reports = [install(pack, args.target, skip_existing=True)
                       for pack in select_packs(args.task, args.profile)]
            print(json.dumps(reports, ensure_ascii=False))
        except (ValueError, OSError) as error:
            parser.exit(2, f"Fehler: {error}\n")
        return 0
    if not args.pack or not args.target:
        parser.error("--pack und --target sind für die Installation erforderlich")
    try:
        print(json.dumps(install(args.pack, args.target, skip_existing=args.skip_existing), ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.exit(2, f"Fehler: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
