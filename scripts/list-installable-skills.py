#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Define the one canonical set of setup directories that are installable runtime skills.
# SCOPE: List direct skills/ children that contain a regular SKILL.md file.
# DEPENDS: Python standard library and the repository skills tree.
# END_MODULE_CONTRACT
"""Print installable setup skills as names or absolute source paths."""

from __future__ import annotations

import argparse
from pathlib import Path


def skill_sources(setup_dir: Path) -> dict[str, Path]:
    root = setup_dir / "skills"
    return {
        directory.name: directory.resolve()
        for directory in sorted(root.iterdir())
        if directory.is_dir() and (directory / "SKILL.md").is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--names", action="store_true")
    args = parser.parse_args()
    sources = skill_sources(args.setup_dir.resolve())
    for name, path in sources.items():
        print(name if args.names else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_MODULE_CONTRACT
