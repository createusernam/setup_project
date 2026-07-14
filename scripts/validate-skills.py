#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate skill frontmatter against explicit Claude-runtime or portable profiles.
# SCOPE: Parse every selected SKILL.md, enforce profile keys and core field types, and report all failures.
# DEPENDS: Python 3 and PyYAML; repository skills use YAML features that require a real parser.
# END_MODULE_CONTRACT
"""Runtime-aware validation for setup skill frontmatter."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only on incomplete dev environments
    raise SystemExit("validate-skills: PyYAML is required (`python3 -m pip install PyYAML`)") from exc


# START_BLOCK_PROFILE_SCHEMA
PORTABLE_KEYS = {
    "allowed-tools",
    "argument-hint",
    "description",
    "license",
    "metadata",
    "name",
}

CLAUDE_KEYS = PORTABLE_KEYS | {
    "agent",
    "context",
    "disable-model-invocation",
    "hooks",
    "model",
    "user-invocable",
}

PROFILE_KEYS = {"claude": CLAUDE_KEYS, "portable": PORTABLE_KEYS}
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# END_BLOCK_PROFILE_SCHEMA


# START_BLOCK_VALIDATION
def parse_frontmatter(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"cannot read file: {exc}"]
    match = FRONTMATTER.match(content)
    if not match:
        return None, ["missing or unterminated YAML frontmatter"]
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return None, [f"invalid YAML: {exc}"]
    if not isinstance(data, dict):
        return None, ["frontmatter must be a mapping"]
    return data, []


def validate_skill(path: Path, profile: str) -> list[str]:
    data, errors = parse_frontmatter(path)
    if data is None:
        return errors

    allowed = PROFILE_KEYS[profile]
    unexpected = sorted(set(data) - allowed)
    if unexpected:
        errors.append(f"unsupported {profile} key(s): {', '.join(unexpected)}")

    name = data.get("name")
    if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
        errors.append("name must be non-empty hyphen-case")
    elif path.parent.name != name:
        errors.append(f"name {name!r} does not match directory {path.parent.name!r}")

    description = data.get("description")
    if not isinstance(description, str) or len(description.strip()) < 50:
        errors.append("description must be a string of at least 50 characters")
    elif len(description) > 1024:
        errors.append("description exceeds 1024 characters")

    for key in ("user-invocable", "disable-model-invocation"):
        if key in data and not isinstance(data[key], bool):
            errors.append(f"{key} must be boolean")
    for key in ("hooks", "metadata"):
        if key in data and not isinstance(data[key], dict):
            errors.append(f"{key} must be a mapping")
    if "allowed-tools" in data and not isinstance(data["allowed-tools"], (str, list)):
        errors.append("allowed-tools must be a string or list")
    return errors
# END_BLOCK_VALIDATION


# START_BLOCK_CLI
def discover_skill_files(paths: list[Path]) -> list[Path]:
    discovered: set[Path] = set()
    for path in paths:
        if path.is_file():
            discovered.add(path)
        elif (path / "SKILL.md").is_file():
            discovered.add(path / "SKILL.md")
        elif path.is_dir():
            discovered.update(path.glob("*/SKILL.md"))
    return sorted(discovered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("skills")])
    parser.add_argument("--profile", choices=sorted(PROFILE_KEYS), default="claude")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    files = discover_skill_files(args.paths)
    if not files:
        print("validate-skills: no SKILL.md files found", file=sys.stderr)
        return 2

    failures = 0
    for path in files:
        errors = validate_skill(path, args.profile)
        if errors:
            failures += 1
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
    if failures:
        print(f"FAIL: {failures}/{len(files)} skill(s) invalid for profile {args.profile}")
        return 1
    print(f"PASS: {len(files)} skill(s) valid for profile {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
