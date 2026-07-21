#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Build canonical iteration dashboard JSON and deterministic human Markdown in the existing supervision track.
# SCOPE: Read trusted Phase 6 artifacts, derive status/metrics/links, emit a viewpoint, and update the managed SUPERVISION index section.
# DEPENDS: Python standard library, Phase 6 JSON artifacts, dashboard/viewpoint schemas, and visualization conventions.
# END_MODULE_CONTRACT
"""Render the trusted Phase 6 iteration dashboard."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SUPERVISION_LINK = "[Current iteration dashboard](dashboard.md)"

__all__ = ("build_dashboard",)

# START_CONTRACT: build_dashboard
# PURPOSE: Derive the canonical human supervision dashboard from Phase 6 evidence.
# PRE: The project contains all required Phase 6 artifacts.
# POST: Returns deterministic dashboard and viewpoint documents without writing them.
# END_CONTRACT: build_dashboard


def load(project: Path, name: str) -> dict[str, Any]:
    path = project / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {name}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain an object")
    return value


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "iteration"


def derive_status(
    budget: dict[str, Any], integrity: dict[str, Any], review: dict[str, Any],
    evidence: dict[str, Any], expected_ids: list[str], actual_items: list[dict[str, Any]],
    commands_exact: bool,
) -> str:
    if budget.get("verdict") == "SPLIT_REQUIRED":
        return "SPLIT_REQUIRED"
    if integrity.get("verdict") == "CONTRACT_GAP":
        return "CONTRACT_GAP"
    if review.get("acceptor", {}).get("verdict") == "RESTART":
        return "RESTART"
    review_verdicts = [review.get("mechanical", {}).get("verdict"), review.get("architect", {}).get("verdict"), review.get("test_owner", {}).get("verdict"), review.get("acceptor", {}).get("verdict")]
    actual_ids = [item.get("id") for item in actual_items]
    exact_criteria = (
        len(actual_ids) == len(set(actual_ids))
        and set(actual_ids) == set(expected_ids)
        and all(item.get("status") == "PASS" for item in actual_items)
    )
    checks = evidence.get("checks", [])
    checks_pass = isinstance(checks, list) and bool(checks) and commands_exact and all(
        isinstance(item, dict) and item.get("status") == "pass" for item in checks
    )
    deltas_closed = (
        evidence.get("requirements_delta", {}).get("status") in {"none", "resolved"}
        and evidence.get("debt_delta", {}).get("status") in {"none", "resolved", "accepted"}
    )
    scaffold_status = evidence.get("scaffold_integrity", {}).get("status")
    integrity_closed = (
        integrity.get("verdict") == "PASS" and scaffold_status == "unchanged"
    ) or (
        integrity.get("verdict") == "SCAFFOLD_DRIFT" and scaffold_status == "architect_approved"
    )
    complete = (
        budget.get("verdict") == "PASS"
        and all(value == "PASS" for value in review_verdicts)
        and evidence.get("status") == "complete"
        and exact_criteria and checks_pass and deltas_closed and integrity_closed
    )
    return "PASS" if complete else "REVISE"


def build_dashboard(project: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    iteration = load(project, "iteration-contract.json")
    contract = load(project, "contract.json")
    budget = load(project, "iteration-budget.json")
    integrity = load(project, "scaffold-integrity.json")
    review = load(project, "iteration-review.json")
    evidence = load(project, "build-evidence.json")
    expected = [item.get("id") for item in contract.get("criteria", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
    evidence_items = [item for item in evidence.get("criteria", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
    actual_items = {item.get("id"): item for item in evidence_items}
    must_pass = [item.get("id") for item in contract.get("criteria", []) if isinstance(item, dict) and item.get("must_pass") is True]
    missing = sorted(set(expected) - set(actual_items))
    failed = sorted(item_id for item_id, item in actual_items.items() if item.get("status") != "PASS")
    passed_must = sum(1 for item_id in must_pass if actual_items.get(item_id, {}).get("status") == "PASS")
    required_commands = iteration.get("verify_commands", [])
    observed_commands = [
        item.get("command") for item in evidence.get("checks", [])
        if isinstance(item, dict) and isinstance(item.get("command"), str)
    ]
    commands_exact = (
        isinstance(required_commands, list)
        and len(observed_commands) == len(set(observed_commands))
        and set(observed_commands) == set(required_commands)
    )
    status = derive_status(budget, integrity, review, evidence, expected, evidence_items, commands_exact)
    actions = {
        "PASS": "Proceed to Phase 7 independent feature/code review.",
        "REVISE": "Return the bounded leaf to the worker with the recorded review blockers.",
        "SPLIT_REQUIRED": "Stop implementation and split the issue into smaller PBS leaves.",
        "CONTRACT_GAP": "Return to the owning upstream planning/scaffold phase and re-attest changed contracts.",
        "RESTART": "Archive the failed iteration and start a fresh worker context from the iteration baseline.",
    }
    evidence_refs = [item.get("evidence_ref") for item in actual_items.values() if isinstance(item.get("evidence_ref"), str)]
    traces = sorted(set(evidence.get("trace_refs", [])) | {ref for ref in evidence_refs if ref.endswith(".log")})
    screenshots = sorted({ref for ref in evidence_refs if ref.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))})
    critique_paths = sorted(
        project.glob(".build-loop/iterations/*/critique.json"),
        key=lambda path: (path.parent.name.isdigit(), int(path.parent.name) if path.parent.name.isdigit() else -1, str(path)),
    )
    critique = next((str(path.relative_to(project)) for path in critique_paths[-1:]), None)
    models = {role: review.get(role, {}).get("model_id", iteration.get("models", {}).get(role, "")) for role in ("worker", "architect", "test_owner", "acceptor")}
    view_id = f"iteration-{slug(str(iteration['issue_id']))}"
    dashboard = {
        "$schema": "./iteration-dashboard.schema.json", "version": "1",
        "producer": "trusted-iteration-dashboard-renderer",
        "consumers": ["human-supervision", "phase6-semantic-validator"],
        "view_id": view_id, "status": status, "issue_id": iteration["issue_id"],
        "pbs_leaf": iteration["pbs_leaf"], "goal": iteration["goal"], "models": models,
        "budget": budget.get("budget", {}),
        "criteria": {"coverage": f"{len(set(expected) & set(actual_items))}/{len(expected)}", "must_pass": f"{passed_must}/{len(must_pass)}", "missing": missing, "failed": failed},
        "tests": evidence.get("checks", []), "trace_evidence": traces,
        "requirements_delta": evidence.get("requirements_delta", {}),
        "architecture_delta": {"verdict": integrity.get("verdict"), "violations": integrity.get("violations", []), "gap": integrity.get("gap")},
        "debt_delta": evidence.get("debt_delta", {}),
        "links": {"diff": f"git-diff:{budget.get('baseline_commit', 'unknown')}..working-tree", "critique": critique, "screenshots": screenshots, "traces": traces},
        "human_summary": f"{status}: {iteration['goal']} ({iteration['pbs_leaf']}).",
        "worker_explanation": evidence.get("worker_explanation", ""),
        "uncertainty": evidence.get("residual_risks", []), "legal_next_action": actions[status],
    }
    viewpoint = {
        "$schema": "../../viewpoint.schema.json", "version": "1", "view_id": view_id,
        "stakeholder": "phase6_supervisor", "decision": "whether this bounded worker iteration may advance",
        "story_ref": iteration["story_refs"][0], "concern": "dynamics", "scale": "operation",
        "focal_elements": ["scope_and_budget", "evidence_and_deltas", "review_chain"],
        "actors": ["worker", "architect", "test_owner", "acceptor", "human_supervisor"],
        "metaphor": None, "canonical_refs": ["iteration-dashboard.json", "iteration-contract.json", "build-evidence.json"],
        "hidden_aggregation": ["full diff content", "full test logs", "model reasoning traces"],
        "next_scale_views": [], "approval": {"status": "draft", "by": None, "at": None},
    }
    return dashboard, viewpoint


def validate(document: dict[str, Any], schema_name: str) -> list[str]:
    spec = importlib.util.spec_from_file_location("dashboard_json_schema", ROOT / "scripts" / "json_schema.py")
    if spec is None or spec.loader is None:
        return ["cannot load trusted JSON Schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = json.loads((ROOT / "templates" / "project" / schema_name).read_text(encoding="utf-8"))
    return module.validate(document, schema)


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown(dashboard: dict[str, Any]) -> str:
    lines = [
        f"# Iteration dashboard — {dashboard['issue_id']}", "",
        f"**Status:** `{dashboard['status']}`  ", f"**Goal:** {dashboard['goal']}  ",
        f"**PBS leaf:** `{dashboard['pbs_leaf']}`", "", "## Models", "",
        "| Role | Model ID |", "|---|---|",
    ]
    lines += [f"| {role} | `{cell(model)}` |" for role, model in dashboard["models"].items()]
    lines += ["", "## Budget", "", "| Metric | Actual | Target | Hard max |", "|---|---:|---:|---:|"]
    lines += [f"| {name} | {metric['actual']} | {metric['target']} | {metric['max']} |" for name, metric in dashboard["budget"].items()]
    criteria = dashboard["criteria"]
    lines += ["", "## Criteria and evidence", "", "| Metric | Result |", "|---|---|", f"| Coverage | {criteria['coverage']} |", f"| Must-pass | {criteria['must_pass']} |", f"| Missing | {cell(', '.join(criteria['missing']) or 'none')} |", f"| Failed | {cell(', '.join(criteria['failed']) or 'none')} |", "", "## Checks", "", "| Command | Status | Evidence |", "|---|---|---|"]
    lines += [f"| {cell(item.get('command', ''))} | {cell(item.get('status', ''))} | {cell(item.get('evidence_ref', ''))} |" for item in dashboard["tests"]]
    lines += ["", "## Deltas", "", "| Delta | Status |", "|---|---|", f"| Requirements | {cell(dashboard['requirements_delta'].get('status', 'unknown'))} |", f"| Architecture | {cell(dashboard['architecture_delta'].get('verdict', 'unknown'))} |", f"| Debt | {cell(dashboard['debt_delta'].get('status', 'unknown'))} |", "", "## Evidence links", "", f"- Diff: `{dashboard['links']['diff']}`", f"- Critique: `{dashboard['links']['critique'] or 'not recorded'}`", f"- Screenshots: {', '.join(dashboard['links']['screenshots']) or 'none'}", f"- Traces: {', '.join(dashboard['links']['traces']) or 'none'}", "", "## Summary", "", dashboard["human_summary"], "", f"Legal next action: **{dashboard['legal_next_action']}**", ""]
    if dashboard["worker_explanation"]:
        lines += ["Worker explanation (untrusted):", "", dashboard["worker_explanation"], ""]
    if dashboard["uncertainty"]:
        lines += ["Uncertainty:", ""] + [f"- {cell(item)}" for item in dashboard["uncertainty"]] + [""]
    return "\n".join(lines)


def check_outputs(project: Path, dashboard: dict[str, Any], viewpoint: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    dashboard_json = project / "iteration-dashboard.json"
    dashboard_md = project / "iterations" / dashboard["issue_id"] / "dashboard.md"
    viewpoint_path = project / "docs" / "views" / f"{dashboard['view_id']}.json"
    expected_json = json.dumps(dashboard, indent=2, sort_keys=True) + "\n"
    expected_md = markdown(dashboard)
    expected_viewpoint = json.dumps(viewpoint, indent=2, sort_keys=True) + "\n"
    current_dashboard_md = project / "dashboard.md"
    for path, expected in ((dashboard_json, expected_json), (dashboard_md, expected_md), (current_dashboard_md, expected_md), (viewpoint_path, expected_viewpoint)):
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            failures.append(f"stale or missing generated dashboard artifact: {path.relative_to(project)}")
    supervision = project / "SUPERVISION.md"
    current_supervision = supervision.read_text(encoding="utf-8") if supervision.is_file() else ""
    if SUPERVISION_LINK not in current_supervision:
        failures.append("SUPERVISION.md is missing the stable current-dashboard link")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    try:
        dashboard, viewpoint = build_dashboard(project)
        errors = validate(dashboard, "iteration-dashboard.schema.json") + validate(viewpoint, "viewpoint.schema.json")
        supervision = project / "SUPERVISION.md"
        if not supervision.is_file() or SUPERVISION_LINK not in supervision.read_text(encoding="utf-8"):
            errors.append("SUPERVISION.md is missing the stable current-dashboard link")
    except (KeyError, OSError, ValueError) as error:
        print(f"[iteration-dashboard] ERROR: {error}")
        return 1
    if errors:
        print("[iteration-dashboard] ERROR: generated artifacts failed schema validation")
        for error in errors:
            print(f"- {error}")
        return 1
    if args.check:
        failures = check_outputs(project, dashboard, viewpoint)
        if failures:
            print("[iteration-dashboard] STALE")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("[iteration-dashboard] PASS current")
        return 0
    dashboard_json = project / "iteration-dashboard.json"
    dashboard_json.write_text(json.dumps(dashboard, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dashboard_md = project / "iterations" / dashboard["issue_id"] / "dashboard.md"
    dashboard_md.parent.mkdir(parents=True, exist_ok=True)
    rendered_markdown = markdown(dashboard)
    dashboard_md.write_text(rendered_markdown, encoding="utf-8")
    (project / "dashboard.md").write_text(rendered_markdown, encoding="utf-8")
    viewpoint_path = project / "docs" / "views" / f"{dashboard['view_id']}.json"
    viewpoint_path.parent.mkdir(parents=True, exist_ok=True)
    viewpoint_path.write_text(json.dumps(viewpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[iteration-dashboard] {dashboard['status']} -> {dashboard_md.relative_to(project)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
