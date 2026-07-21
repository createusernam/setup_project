#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate one canonical iteration contract against approved issue, scaffold, contract, and model bindings.
# SCOPE: Read project artifacts, enforce one issue/PBS lineage and trusted hashes, and never mutate state.
# DEPENDS: Python standard library, setup JSON Schema validator, and Phase 4/5/5.5 project artifacts.
# END_MODULE_CONTRACT
"""Trusted read-only validator for iteration-contract.json."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]

__all__ = ("validate",)

# START_CONTRACT: validate
# PURPOSE: Verify the one-leaf iteration contract produced by scaffold phase 5.5.
# PRE: The project contains the upstream contract and manifests.
# POST: Returns deterministic lineage and budget failures without mutation.
# END_CONTRACT: validate


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing {path.name}")
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot read {path.name}: {error}")
        return {}
    if not isinstance(document, dict):
        failures.append(f"{path.name} must contain an object")
        return {}
    return document


def schema_errors(document_path: Path) -> list[str]:
    module_path = ROOT / "scripts" / "json_schema.py"
    spec = importlib.util.spec_from_file_location("iteration_json_schema", module_path)
    if spec is None or spec.loader is None:
        return ["cannot load trusted JSON Schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = ROOT / "templates" / "project" / "iteration-contract.schema.json"
    return [f"schema: {error}" for error in module.validate_file(document_path, schema)]


def validate(project: Path) -> list[str]:
    failures: list[str] = []
    paths = {
        "iteration": project / "iteration-contract.json",
        "contract": project / "contract.json",
        "issues": project / "issues-manifest.json",
        "scaffold": project / "scaffold-manifest.json",
        "bindings": project / "model-bindings.json",
    }
    documents = {name: load_json(path, failures) for name, path in paths.items()}
    if failures:
        return failures
    failures.extend(schema_errors(paths["iteration"]))
    iteration = documents["iteration"]
    if iteration.get("status") != "ready":
        failures.append("iteration-contract.json status must be ready")

    for field, source in (
        ("contract_sha256", "contract"),
        ("issues_manifest_sha256", "issues"),
        ("scaffold_manifest_sha256", "scaffold"),
    ):
        if iteration.get(field) != sha256(paths[source]):
            failures.append(f"{field} does not match {paths[source].name}")

    issue_id = iteration.get("issue_id")
    matching_issues = [
        issue for issue in documents["issues"].get("issues", [])
        if isinstance(issue, dict) and issue.get("id") == issue_id
    ]
    issue: dict[str, Any] | None = None
    if len(matching_issues) != 1:
        failures.append("issue_id must select exactly one approved issue")
    else:
        issue = matching_issues[0]
        if issue.get("pbs_leaf") != iteration.get("pbs_leaf"):
            failures.append("pbs_leaf does not match approved issue")
        issue_story_refs = set(issue.get("story_refs", [])) | set(issue.get("technical_enabler_for", []))
        if set(iteration.get("story_refs", [])) != issue_story_refs:
            failures.append("story_refs do not match approved issue")
        if set(iteration.get("criterion_refs", [])) != set(issue.get("criterion_refs", [])):
            failures.append("criterion_refs do not match approved issue")

    contract_ids = {
        item.get("id") for item in documents["contract"].get("criteria", []) if isinstance(item, dict)
    }
    unknown_criteria = sorted(set(iteration.get("criterion_refs", [])) - contract_ids)
    if unknown_criteria:
        failures.append(f"unknown contract criterion refs: {', '.join(unknown_criteria)}")

    scaffold_files = [
        item for item in documents["scaffold"].get("files", []) if isinstance(item, dict)
    ]
    if documents["scaffold"].get("issue_id") != issue_id:
        failures.append("issue_id does not match scaffold manifest")
    if any(item.get("pbs_leaf") != iteration.get("pbs_leaf") for item in scaffold_files):
        failures.append("pbs_leaf does not match scaffold files")
    manifest_paths = {item.get("path") for item in scaffold_files if isinstance(item.get("path"), str)}
    if set(iteration.get("scaffold_files", [])) != manifest_paths:
        failures.append("scaffold_files do not match scaffold manifest")

    for field in ("allowed_paths", "forbidden_paths"):
        for value in iteration.get(field, []):
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                failures.append(f"unsafe {field} entry: {value}")
    if not set(iteration.get("verify_commands", [])).issubset(set(iteration.get("allowed_commands", []))):
        failures.append("verify_commands must be a subset of allowed_commands")
    network_policy = iteration.get("network_policy", {})
    if network_policy.get("mode") == "deny" and network_policy.get("allowed_hosts"):
        failures.append("deny network policy requires empty allowed_hosts")
    for label, target_field, max_field in (
        ("production LOC", "production_loc_target", "production_loc_max"),
        ("total LOC", "total_loc_target", "total_loc_max"),
        ("files", "files_target", "max_files"),
        ("public interfaces", "public_interfaces_target", "max_public_interfaces"),
    ):
        target = iteration.get(target_field)
        maximum = iteration.get(max_field)
        if isinstance(target, int) and isinstance(maximum, int) and target > maximum:
            failures.append(f"{label} target exceeds max")

    bindings = documents["bindings"].get("bindings", {})
    model_profiles = {
        "architect": "reasoning_high",
        "worker": "implementation_general",
        "test_owner": "review_test",
        "acceptor": "review_acceptance",
    }
    iteration_models = iteration.get("models", {})
    for role, profile in model_profiles.items():
        binding = bindings.get(profile, {}) if isinstance(bindings, dict) else {}
        if not isinstance(binding, dict) or binding.get("enabled") is not True:
            failures.append(f"{role} profile {profile} must be enabled")
        elif iteration_models.get(role) != binding.get("model_id"):
            failures.append(f"{role} model does not match {profile} binding")
    independent_models = [iteration_models.get(role) for role in ("worker", "test_owner", "acceptor")]
    if None not in independent_models and len(set(independent_models)) != len(independent_models):
        failures.append("worker, test_owner, and acceptor model IDs must be distinct")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    failures = validate(args.project.resolve())
    if failures:
        print("[iteration-contract] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[iteration-contract] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
