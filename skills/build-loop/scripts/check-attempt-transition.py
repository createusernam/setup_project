#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Archive trusted supervision evidence for one bounded build-loop attempt and gate another worker attempt.
# SCOPE: Combine deterministic evaluator, budget, scaffold, and architect checkpoint evidence into attempt-local views.
# DEPENDS: Python standard library, verdict.sh, trusted Phase-6 reports, and .build-loop iteration state.
# END_MODULE_CONTRACT
"""Fail closed between bounded build-loop worker attempts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any


# START_BLOCK_INPUT_VALIDATION
def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def evaluator_verdict(project: Path, iteration: int) -> dict[str, Any]:
    result = subprocess.run(
        ["bash", str(Path(__file__).with_name("verdict.sh")), str(iteration)],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "verdict.sh failed")
    try:
        verdict = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(f"verdict.sh returned invalid JSON: {error}") from error
    if not isinstance(verdict, dict) or verdict.get("verdict") not in {"pass", "continue", "fail", "restart", "abort"}:
        raise ValueError("verdict.sh returned an unsupported verdict")
    return verdict


def trusted_report(project: Path, name: str, producer: str, verdicts: set[str]) -> dict[str, Any]:
    report = read_object(project / name)
    if report.get("producer") != producer:
        raise ValueError(f"{name} has untrusted producer {report.get('producer')!r}")
    if report.get("verdict") not in verdicts:
        raise ValueError(f"{name} has unsupported verdict {report.get('verdict')!r}")
    return report


def report_lineage_errors(iteration: dict[str, Any], *reports: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for report in reports:
        for field in ("issue_id", "pbs_leaf"):
            if report.get(field) != iteration.get(field):
                failures.append(
                    f"trusted report lineage mismatch: {field}={report.get(field)!r}, "
                    f"expected {iteration.get(field)!r}"
                )
    return failures


def architect_checkpoint(path: Path) -> tuple[dict[str, Any], list[str]]:
    checkpoint = read_object(path)
    failures: list[str] = []
    if checkpoint.get("version") != "1" or checkpoint.get("producer") != "architect":
        failures.append("architect checkpoint has invalid version or producer")
    if checkpoint.get("verdict") not in {"CONTINUE", "REVISE", "CONTRACT_GAP", "RESTART"}:
        failures.append("architect checkpoint has unsupported verdict")
    for field in ("model_id", "context_id", "review_ref"):
        if not isinstance(checkpoint.get(field), str) or not checkpoint[field].strip():
            failures.append(f"architect checkpoint requires {field}")
    checks = checkpoint.get("checks")
    if not isinstance(checks, dict):
        return checkpoint, failures + ["architect checkpoint requires checks"]
    for field in ("one_leaf", "boundaries_interfaces", "explanation_matches_evidence"):
        if not isinstance(checks.get(field), bool):
            failures.append(f"architect checkpoint check {field} must be boolean")
    allowed_deltas = {
        "requirements_delta": {"none", "resolved", "material"},
        "architecture_delta": {"none", "resolved", "material"},
        "debt_delta": {"none", "resolved", "accepted", "blocked"},
    }
    for field, allowed in allowed_deltas.items():
        if checks.get(field) not in allowed:
            failures.append(f"architect checkpoint check {field} is invalid")
    return checkpoint, failures
# END_BLOCK_INPUT_VALIDATION


# START_BLOCK_TRANSITION_DECISION
def decision(
    evaluator: dict[str, Any],
    budget: dict[str, Any],
    scaffold: dict[str, Any],
    architect: dict[str, Any] | None,
    architect_failures: list[str],
) -> tuple[str, str, bool]:
    budget_verdict = str(budget["verdict"])
    if budget_verdict != "PASS":
        return budget_verdict, "return to PBS planning; do not start another worker attempt", False
    scaffold_verdict = str(scaffold["verdict"])
    if scaffold_verdict != "PASS":
        return scaffold_verdict, "return to the Phase 5.5 architect; do not start another worker attempt", False

    evaluator_status = evaluator["verdict"]
    if evaluator_status == "pass":
        return "PASS", "enter terminal ordered review; do not start another worker attempt", False
    if evaluator_status == "restart":
        return "RESTART", "restart from the trusted baseline in a fresh worker context", False
    if evaluator_status == "abort":
        return "ABORT", "stop the loop and return to the human owner", False
    if evaluator_status == "fail":
        return "REVISE", "return to the owning contract or plan authority; do not start another worker attempt", False

    if architect is None or architect_failures:
        detail = "; ".join(architect_failures) if architect_failures else "checkpoint is missing"
        return "REVISE", f"obtain a valid architect checkpoint ({detail}) before another worker attempt", False
    architect_status = architect["verdict"]
    if architect_status != "CONTINUE":
        action = {
            "CONTRACT_GAP": "return to the requirements authority; do not start another worker attempt",
            "RESTART": "restart from the trusted baseline in a fresh worker context",
            "REVISE": "resolve the architect review; do not start another worker attempt",
        }[architect_status]
        return str(architect_status), action, False

    checks = architect["checks"]
    if checks["requirements_delta"] == "material":
        return "CONTRACT_GAP", "return to the requirements authority; do not start another worker attempt", False
    if checks["architecture_delta"] == "material":
        return "REVISE", "return to the architecture authority; do not start another worker attempt", False
    if checks["debt_delta"] == "blocked":
        return "REVISE", "resolve or explicitly accept the debt delta before another worker attempt", False
    if not all(checks[field] for field in ("one_leaf", "boundaries_interfaces", "explanation_matches_evidence")):
        return "REVISE", "resolve the failed architect checks before another worker attempt", False
    return "CONTINUE", "start the next bounded worker attempt with this checkpoint as authority", True
# END_BLOCK_TRANSITION_DECISION


# START_BLOCK_RENDER_AND_CLI
def render_markdown(dashboard: dict[str, Any]) -> str:
    architect = dashboard.get("architect") or {}
    checks = architect.get("checks") or {}
    return (
        f"# Attempt {dashboard['iteration']} dashboard\n\n"
        f"**Status:** `{dashboard['status']}`\n\n"
        f"- evaluator: `{dashboard['evaluator']['verdict']}`\n"
        f"- budget: `{dashboard['mechanical']['budget_verdict']}`\n"
        f"- scaffold: `{dashboard['mechanical']['scaffold_verdict']}`\n"
        f"- architect: `{architect.get('verdict', 'MISSING')}`\n"
        f"- requirements delta: `{checks.get('requirements_delta', 'unknown')}`\n"
        f"- architecture delta: `{checks.get('architecture_delta', 'unknown')}`\n"
        f"- debt delta: `{checks.get('debt_delta', 'unknown')}`\n\n"
        f"**Legal next action:** {dashboard['legal_next_action']}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--check-next", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    directory = project / ".build-loop" / "iterations" / str(args.iteration)

    try:
        evaluator = evaluator_verdict(project, args.iteration)
        budget = trusted_report(
            project, "iteration-budget.json", "trusted-iteration-budget-checker",
            {"PASS", "SPLIT_REQUIRED", "SCOPE_BREACH"},
        )
        scaffold = trusted_report(
            project, "scaffold-integrity.json", "trusted-scaffold-integrity-checker",
            {"PASS", "CONTRACT_GAP", "SCAFFOLD_DRIFT"},
        )
        iteration_contract = read_object(project / "iteration-contract.json")
        lineage_failures = report_lineage_errors(iteration_contract, budget, scaffold)
        if lineage_failures:
            raise ValueError("; ".join(lineage_failures))
        checkpoint_path = directory / "architect-checkpoint.json"
        architect, architect_failures = architect_checkpoint(checkpoint_path) if checkpoint_path.is_file() else (None, [])
        status, legal_next_action, next_worker_allowed = decision(
            evaluator, budget, scaffold, architect, architect_failures
        )
    except ValueError as error:
        print(f"[attempt-control] FAIL: {error}")
        return 1

    dashboard = {
        "version": "2",
        "producer": "trusted-attempt-transition-checker",
        "iteration": args.iteration,
        "status": status,
        "evaluator": evaluator,
        "mechanical": {
            "budget_ref": "iteration-budget.json",
            "budget_verdict": budget["verdict"],
            "budget": budget,
            "scaffold_ref": "scaffold-integrity.json",
            "scaffold_verdict": scaffold["verdict"],
            "scaffold": scaffold,
        },
        "architect": architect,
        "architect_validation_errors": architect_failures,
        "legal_next_action": legal_next_action,
        "next_worker_allowed": next_worker_allowed,
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "attempt-dashboard.json").write_text(
        json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (directory / "dashboard.md").write_text(render_markdown(dashboard), encoding="utf-8")

    if args.check_next and not next_worker_allowed:
        print(f"[attempt-control] BLOCKED: {legal_next_action}")
        return 1
    print(f"[attempt-control] {status}: {legal_next_action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_RENDER_AND_CLI
