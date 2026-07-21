#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Enforce Phase 4c human-view prerequisites that depend on the selected route policy.
# SCOPE: Read the project ledger and validate the behavior pack only when the policy requires it.
# DEPENDS: Python standard library, .pipeline-state.json, and check-behavior-pack.py.
# END_MODULE_CONTRACT
"""Trusted read-only Phase 4c visualization validator."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def load_checker(name: str) -> Any:
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(f"phase4c_{path.stem.replace('-', '_')}", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load behavior-pack checker")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def required(tier: object, conditions: object) -> bool:
    return tier in {"T3", "T4"} or isinstance(conditions, dict) and conditions.get("behavior_pack_required") is True


def validate(project: Path) -> list[str]:
    ledger_path = project / ".pipeline-state.json"
    if not ledger_path.is_file():
        return ["missing .pipeline-state.json"]
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read .pipeline-state.json: {error}"]
    policy = ledger.get("policy", {}) if isinstance(ledger, dict) else {}
    if not isinstance(policy, dict):
        return ["malformed policy in .pipeline-state.json"]
    story_checker = load_checker("check-story-trace.py")
    failures = story_checker.check(project)
    if required(policy.get("risk_tier"), policy.get("conditions")):
        failures.extend(load_checker("check-behavior-pack.py").check(project, ROOT))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    failures = validate(args.project.resolve())
    if failures:
        print("[phase4c] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[phase4c] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
