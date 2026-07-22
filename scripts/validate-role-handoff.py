#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate a durable cross-role handoff before it may be consumed by the next Phase 6 role.
# SCOPE: Apply the canonical role-handoff schema to one project-relative or absolute handoff JSON file.
# DEPENDS: scripts/json_schema.py and templates/project/role-handoff.schema.json.
# END_MODULE_CONTRACT
"""Fail closed on malformed Phase 6 role handoffs."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    spec = importlib.util.spec_from_file_location("setup_json_schema", root / "scripts/json_schema.py")
    assert spec and spec.loader
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    errors = validator.validate_file(args.handoff, root / "templates/project/role-handoff.schema.json")
    if errors:
        print("FAIL role handoff")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS role handoff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
