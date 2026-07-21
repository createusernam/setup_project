#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Fail closed when Phase 6 build evidence does not semantically satisfy its contract.
# SCOPE: Read contract and build evidence, report deterministic blockers, and never mutate project state.
# DEPENDS: Python standard library and project contract.json/build-evidence.json.
# END_MODULE_CONTRACT
"""Trusted read-only semantic exit validator for Phase 6."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEBT_TYPES = {
    "new_todo_fixme", "suppression", "skipped_test", "dependency_addition",
    "dead_unreachable_code", "duplication", "public_api_growth", "contract_anchor_drift",
    "test_without_criterion_ref", "criterion_without_executable_evidence",
}


__all__ = ("validate",)


# START_CONTRACT: validate
# PURPOSE: Reject incomplete, untrusted, or untraceable Phase 6 completion evidence.
# PRE: The project contains Phase 6 artifacts and a committed iteration contract.
# POST: Returns every deterministic blocker without mutating project state.
# END_CONTRACT: validate


def load_json(path: Path, label: str, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing {label}: {path}")
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot read {label}: {error}")
        return {}
    if not isinstance(document, dict):
        failures.append(f"{label} must contain a JSON object")
        return {}
    return document


def safe_existing_evidence_ref(project: Path, value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    reference = Path(value)
    if reference.is_absolute() or ".." in reference.parts:
        return False
    candidate = project / reference
    try:
        candidate.resolve().relative_to(project.resolve())
    except ValueError:
        return False
    return candidate.is_file()


def schema_errors(document_path: Path, schema_name: str) -> list[str]:
    module_path = ROOT / "scripts" / "json_schema.py"
    spec = importlib.util.spec_from_file_location("phase6_json_schema", module_path)
    if spec is None or spec.loader is None:
        return ["cannot load trusted JSON Schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = ROOT / "templates" / "project" / schema_name
    return [f"{document_path.name} schema: {error}" for error in module.validate_file(document_path, schema)]


def iteration_review_errors(project: Path) -> list[str]:
    module_path = Path(__file__).with_name("validate-iteration-review.py")
    spec = importlib.util.spec_from_file_location("phase6_iteration_review", module_path)
    if spec is None or spec.loader is None:
        return ["cannot load trusted iteration review validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [f"iteration review: {error}" for error in module.validate(project)]


def iteration_dashboard_errors(project: Path) -> list[str]:
    module_path = ROOT / "skills" / "visualization" / "scripts" / "render-iteration-dashboard.py"
    spec = importlib.util.spec_from_file_location("phase6_iteration_dashboard", module_path)
    if spec is None or spec.loader is None:
        return ["cannot load trusted iteration dashboard renderer"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        dashboard, viewpoint = module.build_dashboard(project)
    except (KeyError, OSError, ValueError) as error:
        return [f"cannot derive trusted iteration dashboard: {error}"]
    failures = module.validate(dashboard, "iteration-dashboard.schema.json")
    failures.extend(module.validate(viewpoint, "viewpoint.schema.json"))
    failures.extend(module.check_outputs(project, dashboard, viewpoint))
    if dashboard.get("status") != "PASS":
        failures.append(f"iteration dashboard status must be PASS, got {dashboard.get('status')}")
    return [f"iteration dashboard: {error}" for error in failures]


def committed_iteration_contract_errors(project: Path) -> list[str]:
    result = subprocess.run(
        ["git", "show", "HEAD:iteration-contract.json"],
        cwd=project, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        return ["iteration-contract.json must be committed at HEAD before Phase 6 exit"]
    try:
        worktree = (project / "iteration-contract.json").read_text(encoding="utf-8")
    except OSError as error:
        return [f"cannot read iteration-contract.json: {error}"]
    if worktree != result.stdout:
        return [
            "iteration-contract.json differs from its committed version; "
            "iteration authority may only change through Phase 5.5 re-attestation"
        ]
    return []


def validate_requirements_delta(delta: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(delta, dict) or delta.get("status") not in {"none", "resolved"}:
        return ["requirements_delta must be none or resolved"]
    items = delta.get("items", [])
    if delta.get("status") == "none" and items:
        failures.append("requirements_delta status none requires zero items")
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id", "<unknown>")
        kind = item.get("type")
        resolution = item.get("resolution", {})
        if not isinstance(resolution, dict):
            continue
        role = resolution.get("authority_role")
        status = resolution.get("status")
        phase = resolution.get("owning_phase")
        required_text = (resolution.get("authority_id"), resolution.get("evidence_ref"))
        if status == "open" or not all(isinstance(value, str) and value.strip() for value in required_text):
            failures.append(f"requirement gap {item_id} is not resolved with attributable evidence")
        if item.get("material") is True and role == "worker":
            failures.append(f"material requirement gap {item_id} cannot be resolved by worker")
        if kind == "implementation_assumption":
            if status == "accepted" and role != "architect":
                failures.append(f"implementation_assumption {item_id} requires architect authority")
        elif kind == "architecture_gap":
            if status != "returned_upstream" or role != "architect" or phase != "2b":
                failures.append(f"architecture_gap {item_id} must return to Phase 2b with architect authority")
        elif kind == "product_gap":
            if status != "returned_upstream" or role != "product_owner" or phase not in {"-1", "4"}:
                failures.append(f"product_gap {item_id} requires product_owner authority and return to Phase -1 or 4")
        elif kind == "evidence_gap":
            routed = status == "returned_upstream" and phase in {"0", "3"} and role in {"research_owner", "architect"}
            risked = status == "accepted_risk" and role in {"risk_owner", "product_owner"}
            if not (routed or risked):
                failures.append(f"evidence_gap {item_id} must return to research/prototype or be accepted_risk")
    return failures


def validate_debt_delta(delta: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(delta, dict) or delta.get("status") not in {"none", "resolved", "accepted"}:
        return ["debt_delta must be none, resolved, or accepted"]
    reviewed = delta.get("reviewed_types", [])
    if not isinstance(reviewed, list) or set(reviewed) != DEBT_TYPES or len(reviewed) != len(DEBT_TYPES):
        failures.append("debt reviewed_types must exactly cover every canonical debt category")
    reviewer = delta.get("reviewer")
    if not isinstance(reviewer, dict) or reviewer.get("role") != "architect" or not all(
        isinstance(reviewer.get(field), str) and reviewer.get(field).strip() for field in ("id", "evidence_ref")
    ):
        failures.append("debt delta requires attributable architect review")
    items = delta.get("items", [])
    if delta.get("status") == "none" and items:
        failures.append("debt_delta status none requires zero items")
    accepted_count = 0
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id", "<unknown>")
        resolution = item.get("resolution", {})
        if not isinstance(resolution, dict):
            continue
        status = resolution.get("status")
        if status == "removed":
            if not isinstance(resolution.get("evidence_ref"), str) or not resolution["evidence_ref"].strip():
                failures.append(f"removed debt {item_id} requires evidence_ref")
        elif status == "owner_accepted":
            accepted_count += 1
            fields = ("owner_id", "reason", "follow_up_task", "evidence_ref")
            if not all(isinstance(resolution.get(field), str) and resolution[field].strip() for field in fields):
                failures.append(
                    f"owner-accepted debt {item_id} requires owner_id, reason, follow_up_task, and evidence_ref"
                )
        else:
            failures.append(f"debt {item_id} remains open")
    if delta.get("status") == "resolved" and accepted_count:
        failures.append("debt_delta status resolved cannot contain owner-accepted debt")
    if delta.get("status") == "accepted" and accepted_count == 0:
        failures.append("debt_delta status accepted requires at least one owner-accepted item")
    return failures


def validate(project: Path) -> list[str]:
    failures: list[str] = []
    contract = load_json(project / "contract.json", "contract.json", failures)
    evidence = load_json(project / "build-evidence.json", "build-evidence.json", failures)
    if failures:
        return failures
    failures.extend(schema_errors(project / "build-evidence.json", "build-evidence.schema.json"))
    if evidence.get("status") != "complete":
        return ["build-evidence.json status must be complete"]

    iteration = load_json(project / "iteration-contract.json", "iteration-contract.json", failures)
    failures.extend(committed_iteration_contract_errors(project))
    budget_ref = evidence.get("iteration_budget_ref")
    budget: dict[str, Any] = {}
    if not isinstance(budget_ref, str) or not budget_ref.strip():
        failures.append("iteration_budget_ref must be non-empty")
    else:
        budget_path = Path(budget_ref)
        if budget_path.is_absolute() or ".." in budget_path.parts:
            failures.append("iteration_budget_ref must be project-relative")
        else:
            resolved_budget = project / budget_path
            budget = load_json(resolved_budget, "iteration budget", failures)
            if budget:
                failures.extend(schema_errors(resolved_budget, "iteration-budget.schema.json"))
                if budget.get("verdict") != "PASS":
                    failures.append("iteration budget verdict must be PASS")
                if budget.get("issue_id") != evidence.get("issue_id"):
                    failures.append("iteration budget issue_id does not match build evidence")
                if budget.get("pbs_leaf") != evidence.get("pbs_leaf"):
                    failures.append("iteration budget pbs_leaf does not match build evidence")
                if budget.get("baseline_commit") != iteration.get("baseline_commit"):
                    failures.append("iteration budget baseline does not match iteration contract")
    for field in ("issue_id", "pbs_leaf"):
        if iteration.get(field) != evidence.get(field):
            failures.append(f"iteration contract {field} does not match build evidence")
    review_ref = evidence.get("iteration_review_ref")
    if review_ref != "iteration-review.json":
        failures.append("iteration_review_ref must be iteration-review.json")
    else:
        failures.extend(iteration_review_errors(project))

    contract_sha = hashlib.sha256((project / "contract.json").read_bytes()).hexdigest()
    if evidence.get("contract_sha256") != contract_sha:
        failures.append("contract_sha256 does not match contract.json")
    for field in ("issue_id", "pbs_leaf"):
        value = evidence.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be non-empty")
    dashboard_ref = evidence.get("iteration_dashboard_ref")
    if not isinstance(dashboard_ref, str) or not dashboard_ref.strip():
        failures.append("iteration_dashboard_ref must be non-empty")
    else:
        dashboard_path = Path(dashboard_ref)
        if dashboard_path.is_absolute() or ".." in dashboard_path.parts:
            failures.append("iteration_dashboard_ref must be project-relative")
        elif not (project / dashboard_path).is_file():
            failures.append(f"iteration dashboard is missing: {dashboard_ref}")
    if evidence.get("iteration_dashboard_json_ref") != "iteration-dashboard.json":
        failures.append("iteration_dashboard_json_ref must be iteration-dashboard.json")
    else:
        failures.extend(iteration_dashboard_errors(project))
    failures.extend(validate_requirements_delta(evidence.get("requirements_delta")))
    failures.extend(validate_debt_delta(evidence.get("debt_delta")))
    scaffold = evidence.get("scaffold_integrity")
    if not isinstance(scaffold, dict) or scaffold.get("status") not in {"unchanged", "architect_approved"}:
        failures.append("scaffold integrity must be unchanged or architect_approved")
    else:
        report_ref = scaffold.get("report_ref")
        integrity: dict[str, Any] = {}
        if not isinstance(report_ref, str) or not report_ref.strip():
            failures.append("scaffold integrity report_ref must be non-empty")
        else:
            report_path = Path(report_ref)
            if report_path.is_absolute() or ".." in report_path.parts:
                failures.append("scaffold integrity report_ref must be project-relative")
            else:
                resolved_report = project / report_path
                integrity = load_json(resolved_report, "scaffold integrity report", failures)
                if integrity:
                    failures.extend(schema_errors(resolved_report, "scaffold-integrity.schema.json"))
                    for field in ("issue_id", "pbs_leaf", "baseline_commit"):
                        expected = iteration.get(field) if field == "baseline_commit" else evidence.get(field)
                        if integrity.get(field) != expected:
                            failures.append(f"scaffold integrity {field} does not match iteration evidence")
                    verdict = integrity.get("verdict")
                    if verdict == "CONTRACT_GAP":
                        failures.append("scaffold integrity CONTRACT_GAP must return to Phase 5.5")
                    elif verdict == "SCAFFOLD_DRIFT" and scaffold.get("status") != "architect_approved":
                        failures.append("SCAFFOLD_DRIFT requires architect_approved build evidence")
                    elif verdict == "PASS" and scaffold.get("status") != "unchanged":
                        failures.append("PASS scaffold integrity must be recorded as unchanged")
        if scaffold.get("status") == "architect_approved":
            review_ref = scaffold.get("architect_review_ref")
            if not isinstance(review_ref, str) or not review_ref.strip():
                failures.append("architect-approved scaffold drift requires architect_review_ref")
            else:
                review_path = Path(review_ref)
                if review_path.is_absolute() or ".." in review_path.parts or not (project / review_path).is_file():
                    failures.append("architect_review_ref must name an existing project-relative file")

    checks = evidence.get("checks", [])
    if not isinstance(checks, list) or not checks:
        failures.append("complete build evidence requires at least one required check")
        checks = []
    for check in checks:
        if not isinstance(check, dict):
            failures.append("every required check must be an object")
            continue
        status = check.get("status")
        if status != "pass":
            failures.append(f"required check {check.get('command')!r} is {status}")
        if not safe_existing_evidence_ref(project, check.get("evidence_ref")):
            failures.append(f"required check {check.get('command')!r} evidence_ref must name an existing project-relative file")
    required_commands = iteration.get("verify_commands", [])
    if not isinstance(required_commands, list):
        failures.append("iteration verify_commands must be an array")
        required_commands = []
    observed_commands = [
        check.get("command") for check in checks
        if isinstance(check, dict) and isinstance(check.get("command"), str)
    ]
    duplicate_commands = sorted({command for command in observed_commands if observed_commands.count(command) > 1})
    missing_commands = sorted(set(required_commands) - set(observed_commands))
    unknown_commands = sorted(set(observed_commands) - set(required_commands))
    if duplicate_commands:
        failures.append(f"duplicate required checks: {', '.join(duplicate_commands)}")
    if missing_commands:
        failures.append(f"missing required checks: {', '.join(missing_commands)}")
    if unknown_commands:
        failures.append(f"unknown required checks: {', '.join(unknown_commands)}")

    criteria = contract.get("criteria", [])
    criteria_by_id: dict[str, dict[str, Any]] = {}
    duplicate_contract_ids: set[str] = set()
    for criterion in criteria:
        if not isinstance(criterion, dict) or not isinstance(criterion.get("id"), str):
            continue
        criterion_id = criterion["id"]
        if criterion_id in criteria_by_id:
            duplicate_contract_ids.add(criterion_id)
        criteria_by_id[criterion_id] = criterion
    for criterion_id in sorted(duplicate_contract_ids):
        failures.append(f"duplicate contract criterion id: {criterion_id}")
    expected_ids = {
        criterion.get("id")
        for criterion in criteria
        if isinstance(criterion, dict) and isinstance(criterion.get("id"), str)
    }
    evidence_items = evidence.get("criteria", [])
    evidence_by_id: dict[str, dict[str, Any]] = {}
    duplicate_evidence_ids: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        criterion_id = item["id"]
        if criterion_id in evidence_by_id:
            duplicate_evidence_ids.add(criterion_id)
        evidence_by_id[criterion_id] = item
        if not safe_existing_evidence_ref(project, item.get("evidence_ref")):
            failures.append(f"criterion {criterion_id} evidence_ref must name an existing project-relative file")
    for criterion_id in sorted(duplicate_evidence_ids):
        failures.append(f"duplicate build criterion id: {criterion_id}")
    actual_ids = {
        item.get("id")
        for item in evidence_items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = sorted(expected_ids - actual_ids)
    unknown = sorted(actual_ids - expected_ids)
    if missing:
        failures.append(f"missing criterion evidence: {', '.join(missing)}")
    if unknown:
        failures.append(f"unknown criterion evidence: {', '.join(unknown)}")
    for criterion_id in sorted(expected_ids & actual_ids):
        status = evidence_by_id[criterion_id].get("status")
        if status != "PASS":
            prefix = "must-pass criterion" if criteria_by_id[criterion_id].get("must_pass") else "criterion"
            failures.append(f"{prefix} {criterion_id} is {status}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    failures = validate(args.project.resolve())
    if failures:
        print("[phase6] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[phase6] PASS semantic build evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
