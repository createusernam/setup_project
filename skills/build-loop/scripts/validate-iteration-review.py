#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate the ordered Phase 6 worker, mechanical, architect, test-owner, and isolated-acceptor chain.
# SCOPE: Enforce exact role identities, responsibilities, stage order/verdicts, fresh contexts, and evidence refs without mutating state.
# DEPENDS: Python standard library, iteration-review.json, iteration-contract.json, model-bindings.json, and trusted JSON Schema validator.
# END_MODULE_CONTRACT
"""Trusted read-only validator for iteration-review.json."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]

__all__ = ("validate",)

# START_CONTRACT: validate
# PURPOSE: Verify the declared ordered independent-review chain for one iteration.
# PRE: The project contains review, contract, and model-binding artifacts.
# POST: Returns deterministic review-chain failures without mutating project state.
# END_CONTRACT: validate


def load(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot read {path.name}: {error}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"{path.name} must contain an object")
        return {}
    return value


def schema_errors(path: Path) -> list[str]:
    spec = importlib.util.spec_from_file_location("review_json_schema", ROOT / "scripts" / "json_schema.py")
    if spec is None or spec.loader is None:
        return ["cannot load trusted JSON Schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_file(path, ROOT / "templates" / "project" / "iteration-review.schema.json")


def safe_existing_ref(project: Path, value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and (project / path).is_file()


def validate(project: Path) -> list[str]:
    failures: list[str] = []
    review_path = project / "iteration-review.json"
    review = load(review_path, failures)
    iteration = load(project / "iteration-contract.json", failures)
    bindings_doc = load(project / "model-bindings.json", failures)
    if failures:
        return failures
    failures.extend(f"schema: {error}" for error in schema_errors(review_path))
    for field in ("issue_id", "pbs_leaf"):
        if review.get(field) != iteration.get(field):
            failures.append(f"review {field} does not match iteration contract")

    stages = ("worker", "mechanical", "architect", "test_owner", "acceptor")
    expected_sequence = {name: index for index, name in enumerate(stages, 1)}
    if any(review.get(name, {}).get("sequence") != index for name, index in expected_sequence.items()):
        failures.append("review stage sequence must be worker=1, mechanical=2, architect=3, test_owner=4, acceptor=5")

    expected_models = iteration.get("models", {})
    role_map = {"worker": "worker", "architect": "architect", "test_owner": "test_owner", "acceptor": "acceptor"}
    for stage, role in role_map.items():
        if review.get(stage, {}).get("model_id") != expected_models.get(role):
            failures.append(f"{stage} model does not match iteration contract")
    bindings = bindings_doc.get("bindings", {})
    profiles = {"worker": "implementation_general", "architect": "reasoning_high", "test_owner": "review_test", "acceptor": "review_acceptance"}
    for stage, profile in profiles.items():
        binding = bindings.get(profile, {}) if isinstance(bindings, dict) else {}
        if review.get(stage, {}).get("model_id") != binding.get("model_id") or binding.get("enabled") is not True:
            failures.append(f"{stage} model does not match enabled {profile} binding")

    identities = [review.get(stage, {}).get("model_id") for stage in ("worker", "test_owner", "acceptor")]
    if None not in identities and len(set(identities)) != len(identities):
        failures.append("worker, test_owner, and acceptor model IDs must be distinct")
    contexts = [review.get(stage, {}).get("context_id") for stage in ("worker", "architect", "test_owner", "acceptor")]
    if None not in contexts and len(set(contexts)) != len(contexts):
        failures.append("review context IDs must be unique")
    if review.get("test_owner", {}).get("fresh_context") is not True:
        failures.append("test_owner must use a fresh context")
    acceptor = review.get("acceptor", {})
    if acceptor.get("fresh_context") is not True or acceptor.get("isolated_context") is not True:
        failures.append("acceptor must use a fresh isolated context")

    if review.get("mechanical", {}).get("verdict") != "PASS":
        failures.append("mechanical verdict must be PASS")
    for stage in ("architect", "test_owner", "acceptor"):
        if review.get(stage, {}).get("verdict") != "PASS":
            failures.append(f"{stage} verdict must be PASS")
    for check, status in review.get("architect", {}).get("checks", {}).items():
        if status is not True:
            failures.append(f"architect check {check} must pass")

    refs = {
        "worker handoff": review.get("worker", {}).get("handoff_ref"),
        "budget": review.get("mechanical", {}).get("budget_ref"),
        "scaffold integrity": review.get("mechanical", {}).get("scaffold_integrity_ref"),
        "architect review": review.get("architect", {}).get("review_ref"),
        "test-owner review": review.get("test_owner", {}).get("review_ref"),
        "acceptor review": review.get("acceptor", {}).get("review_ref"),
    }
    for label, ref in refs.items():
        if not safe_existing_ref(project, ref):
            failures.append(f"{label} ref must name an existing project-relative file")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    failures = validate(args.project.resolve())
    if failures:
        print("[iteration-review] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[iteration-review] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
