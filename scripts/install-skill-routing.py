#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Install or verify one managed cross-CLI skill-routing policy in global agent instructions.
# SCOPE: Preserve user-authored content while replacing a bounded managed block for Claude, Codex, and existing OpenCode instructions.
# DEPENDS: Python standard library and docs/agent/SKILL-ROUTING.md.
# END_MODULE_CONTRACT
"""Install the setup skill-routing contract into global runtime instructions."""

from __future__ import annotations

import argparse
from pathlib import Path
import os
import re
import sys


# START_BLOCK_MANAGED_POLICY
START = "<!-- setup:skill-routing:start -->"
END = "<!-- setup:skill-routing:end -->"
BLOCK = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)


def managed_text(source: Path) -> str:
    content = source.read_text(encoding="utf-8").strip()
    return f"{START}\n{content}\n{END}"


def resolved_target(path: Path) -> Path:
    return path.resolve(strict=False) if path.is_symlink() else path


def target_paths(home: Path) -> list[tuple[str, Path]]:
    targets = [
        ("claude", home / ".claude" / "CLAUDE.md"),
        ("codex", home / ".codex" / "AGENTS.md"),
    ]
    opencode = home / ".config" / "opencode" / "AGENTS.md"
    if opencode.exists() or opencode.is_symlink():
        targets.append(("opencode", opencode))
    return targets


def unique_targets(home: Path) -> list[tuple[list[str], Path]]:
    grouped: dict[Path, list[str]] = {}
    for runtime, path in target_paths(home):
        grouped.setdefault(resolved_target(path), []).append(runtime)
    return [(runtimes, path) for path, runtimes in grouped.items()]


def install_one(path: Path, managed: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if BLOCK.search(existing):
        updated = BLOCK.sub(managed, existing, count=1)
    else:
        separator = "\n\n" if existing.strip() else ""
        updated = existing.rstrip() + separator + managed + "\n"
    if updated == existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(path)


def check_one(path: Path, managed: str) -> bool:
    if not path.is_file():
        return False
    match = BLOCK.search(path.read_text(encoding="utf-8"))
    return bool(match and match.group(0) == managed)
# END_BLOCK_MANAGED_POLICY


# START_BLOCK_CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--home", type=Path, default=Path.home())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        managed = managed_text(args.source)
    except OSError as exc:
        print(f"skill-routing: cannot read {args.source}: {exc}", file=sys.stderr)
        return 2

    failed = False
    for runtimes, path in unique_targets(args.home.expanduser()):
        label = "+".join(runtimes)
        if args.install:
            install_one(path, managed)
            print(f"OK   {label:16} {path}")
        else:
            valid = check_one(path, managed)
            print(f"{'OK' if valid else 'FAIL':4} {label:16} {path}")
            failed = failed or not valid

    opencode = args.home.expanduser() / ".config" / "opencode" / "AGENTS.md"
    if not (opencode.exists() or opencode.is_symlink()):
        print("INFO opencode         no AGENTS.md; OpenCode falls back to the managed Claude instructions")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
