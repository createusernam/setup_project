#!/usr/bin/env python3
"""Validate a Behavior Pack's schema, traceability, links, and readability budgets."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _validator(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("behavior_pack_schema", root / "scripts" / "json_schema.py")
    if spec is None or spec.loader is None:
        raise ValueError("cannot load portable JSON schema validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _file(project: Path, relative: str) -> Path | None:
    path = (project / relative).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError:
        return None
    return path


def check(project: Path, root: Path) -> list[str]:
    index = project / "docs/behavior/behavior-index.json"
    schema = root / "templates/project/docs/behavior/behavior-index.schema.json"
    if not index.is_file():
        return ["behavior_pack: missing docs/behavior/behavior-index.json"]
    errors = [f"behavior_pack: {error}" for error in _validator(root).validate_file(index, schema)]
    if errors:
        return errors
    data = json.loads(index.read_text(encoding="utf-8"))
    flows = {item["id"]: item for item in data["flows"]}
    use_cases = {item["id"]: item for item in data["use_cases"]}
    if len(flows) != len(data["flows"]): errors.append("behavior_pack: duplicate flow id")
    if len(use_cases) != len(data["use_cases"]): errors.append("behavior_pack: duplicate use-case id")
    for kind, items in (("flow", data["flows"]), ("use case", data["use_cases"]), ("interaction", data["interactions"])):
        for item in items:
            path = _file(project, item["path"])
            if path is None or not path.is_file(): errors.append(f"behavior_pack: {kind} {item['id']} references missing file {item['path']!r}")
    for item in data["use_cases"]:
        if item["flow_id"] not in flows: errors.append(f"behavior_pack: use case {item['id']} references unknown flow {item['flow_id']}")
        if len({step["number"] for step in item["steps"]}) != len(item["steps"]): errors.append(f"behavior_pack: use case {item['id']} repeats a step number")
        if item["critical"] and not item["contract_paths"]: errors.append(f"behavior_pack: critical use case {item['id']} has no contract path")
    for flow in data["flows"]:
        for use_case_id in flow["use_case_ids"]:
            if use_case_id not in use_cases: errors.append(f"behavior_pack: flow {flow['id']} references unknown use case {use_case_id}")
    seen: set[str] = set()
    for item in data["interactions"]:
        if item["id"] in seen: errors.append(f"behavior_pack: duplicate interaction id {item['id']}")
        seen.add(item["id"])
        use_case = use_cases.get(item["use_case_id"])
        if use_case is None: errors.append(f"behavior_pack: interaction {item['id']} references unknown use case {item['use_case_id']}")
        elif item["step"] not in {step["number"] for step in use_case["steps"]}: errors.append(f"behavior_pack: interaction {item['id']} references unknown step {item['use_case_id']}/step-{item['step']}")
        if (item["lifeline_count"] > 7 or item["node_count"] > 20 or item["max_nesting"] > 3) and not item["split_justification"]:
            errors.append(f"behavior_pack: SPLIT_REQUIRED for interaction {item['id']} (budget exceeded without justification)")
    if data["coverage"]["uncovered_criteria"] or data["coverage"]["uncovered_critical_error_paths"]:
        errors.append("behavior_pack: coverage has unresolved criteria or critical error paths")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    errors = check(args.project.resolve(), args.root.resolve())
    if errors:
        print("[behavior-pack] INVALID"); print("\n".join(f"- {error}" for error in errors)); return 1
    print("[behavior-pack] PASS"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
