#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Enforce the optional Kaeru memory boundary without making memory canonical pipeline state.
# SCOPE: Validate typed memory references and check promotion provenance; no network or vault writes.
# DEPENDS: Python standard library, json_schema.py, and templates/project/kaeru-memory-ref.schema.json.
# END_MODULE_CONTRACT
"""Validate Kaeru adapter packets and print the safe session read order."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


AUTHORITY_ORDER = ["artifact", "workctl", "kaeru", "session"]
READ_OPERATIONS = ["awake", "overview", "search", "drill"]


def validator(root: Path):
    path = root / "scripts" / "json_schema.py"
    spec = importlib.util.spec_from_file_location("setup_json_schema", path)
    if spec is None or spec.loader is None:
        raise ValueError(
            f"cannot load required validator at {path}; "
            "restore the complete setup checkout; adapter fails closed"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["policy", "validate", "promotion-check"])
    parser.add_argument("packet", nargs="?", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "policy":
        print(json.dumps({
            "authority_order": AUTHORITY_ORDER,
            "session_entry": ["pipeline-status", "named-workctl-task", "kaeru-awake-or-overview-if-needed"],
            "allowed_read_operations": READ_OPERATIONS,
            "writes": "explicit candidate packets only",
            "gate_authority": False,
        }, indent=2))
        return 0
    if args.packet is None or not args.packet.is_file():
        raise ValueError("validate and promotion-check require an existing packet path")
    schema = root / "templates" / "project" / "kaeru-memory-ref.schema.json"
    failures = validator(root).validate_file(args.packet, schema)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    if args.command == "promotion-check":
        if packet["status"] not in {"supported", "settled"}:
            print("FAIL: only supported or settled memory may be proposed for canonical promotion")
            return 1
        if not any(reference.startswith("git:") or "#" in reference for reference in packet["source_refs"]):
            print("FAIL: promotion requires a Git SHA or artifact pointer in source_refs")
            return 1
        print("PASS: promotion may be proposed to the owning producer phase; no gate is opened")
        return 0
    print("PASS: Kaeru memory reference is structurally valid and remains non-canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
