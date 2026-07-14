#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Detect missing, shadowed, or version-divergent setup skills across Claude, Codex, and OpenCode discovery roots.
# SCOPE: Compare setup skill directories with user symlinks and verify the managed global routing policy.
# DEPENDS: Python standard library and install-skill-routing.py.
# END_MODULE_CONTRACT
"""Check that every setup skill resolves to one source in every supported CLI."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from typing import Any


# START_BLOCK_DISCOVERY
def skill_sources(setup_dir: Path) -> dict[str, Path]:
    root = setup_dir / "skills"
    return {
        directory.name: directory.resolve()
        for directory in sorted(root.iterdir())
        if directory.is_dir() and (directory / "SKILL.md").is_file()
    }


def inspect_target(target: Path, expected: Path) -> tuple[bool, str]:
    if not target.exists() and not target.is_symlink():
        return False, "missing"
    if not target.is_symlink():
        return False, "real path shadows setup"
    actual = target.resolve(strict=False)
    if actual != expected:
        return False, f"points to {actual}"
    return True, str(actual)


def load_routing_module(setup_dir: Path) -> Any:
    path = setup_dir / "scripts" / "install-skill-routing.py"
    spec = importlib.util.spec_from_file_location("install_skill_routing", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_discovery(setup_dir: Path, home: Path) -> tuple[list[str], list[str]]:
    sources = skill_sources(setup_dir)
    errors: list[str] = []
    lines: list[str] = []
    roots = {
        "claude": home / ".claude" / "skills",
        "agents": home / ".agents" / "skills",
    }
    for name, expected in sources.items():
        resolved: dict[str, Path] = {}
        for runtime, root in roots.items():
            target = root / name
            valid, detail = inspect_target(target, expected)
            lines.append(f"{'OK' if valid else 'FAIL':4} {runtime:7} {name}: {detail}")
            if not valid:
                errors.append(f"{runtime}/{name}: {detail}")
            elif target.exists():
                resolved[runtime] = target.resolve()
        if len(set(resolved.values())) > 1:
            errors.append(f"{name}: discovery roots resolve to different targets")

    routing = load_routing_module(setup_dir)
    managed = routing.managed_text(setup_dir / "docs" / "agent" / "SKILL-ROUTING.md")
    for runtimes, path in routing.unique_targets(home):
        valid = routing.check_one(path, managed)
        label = "+".join(runtimes)
        lines.append(f"{'OK' if valid else 'FAIL':4} routing {label}: {path}")
        if not valid:
            errors.append(f"routing/{label}: missing or stale managed policy at {path}")
    return errors, lines
# END_BLOCK_DISCOVERY


# START_BLOCK_CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--quiet", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        errors, lines = check_discovery(args.setup_dir.resolve(), args.home.expanduser().resolve())
    except (OSError, RuntimeError) as exc:
        print(f"skill-discovery: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        print("\n".join(lines))
    if errors:
        print(f"FAIL: {len(errors)} discovery/routing issue(s)", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(skill_sources(args.setup_dir.resolve()))} skill(s) share one source across runtimes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
