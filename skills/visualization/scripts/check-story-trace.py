#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate canonical User Story identifiers and their links to Use Cases, criteria, delivery slices, and evidence.
# SCOPE: Read-only validation of docs/stories, views, issues, iteration contracts, and build evidence when those artifacts exist.
# DEPENDS: Python standard library and the repository JSON schema validator.
# END_MODULE_CONTRACT
"""Fail closed on broken canonical User Story traceability."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"cannot read {path.relative_to(path.parent.parent.parent) if path.name == 'index.json' else path.name}: {error}")
        return {}
    return value if isinstance(value, dict) else {}


def schema_errors(path: Path) -> list[str]:
    spec = importlib.util.spec_from_file_location("story_schema", ROOT / "scripts" / "json_schema.py")
    if spec is None or spec.loader is None:
        return ["cannot load JSON schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_file(path, ROOT / "templates" / "project" / "docs" / "stories" / "index.schema.json")


def check(project: Path) -> list[str]:
    failures: list[str] = []
    index_path = project / "docs" / "stories" / "index.json"
    if not index_path.is_file():
        return ["story_trace: missing docs/stories/index.json"]
    failures.extend(f"story_trace: {error}" for error in schema_errors(index_path))
    index = load_json(index_path, failures)
    stories = index.get("stories", [])
    if not isinstance(stories, list):
        return failures + ["story_trace: stories must be an array"]
    story_ids: set[str] = set()
    use_case_ids: set[str] = set()
    story_criteria: dict[str, set[str]] = {}
    for story in stories:
        if not isinstance(story, dict):
            continue
        story_id = story.get("id")
        if story_id in story_ids:
            failures.append(f"story_trace: duplicate story id {story_id}")
        if isinstance(story_id, str):
            story_ids.add(story_id)
            story_criteria[story_id] = set()
        path = project / str(story.get("path", ""))
        if not path.is_file():
            failures.append(f"story_trace: {story_id} references missing story file {story.get('path')!r}")
        for use_case in story.get("use_cases", []) if isinstance(story.get("use_cases"), list) else []:
            if not isinstance(use_case, dict):
                continue
            use_case_id = use_case.get("id")
            if use_case_id in use_case_ids:
                failures.append(f"story_trace: duplicate use-case id {use_case_id}")
            if isinstance(use_case_id, str):
                use_case_ids.add(use_case_id)
            if isinstance(story_id, str):
                story_criteria[story_id].update(
                    value for value in use_case.get("criterion_refs", []) if isinstance(value, str)
                )
    if not story_ids:
        failures.append("story_trace: story index must contain at least one canonical User Story")

    contract_path = project / "contract.json"
    if contract_path.is_file():
        contract = load_json(contract_path, failures)
        contract_ids = {
            criterion.get("id") for criterion in contract.get("criteria", [])
            if isinstance(criterion, dict) and isinstance(criterion.get("id"), str)
        }
        unknown_story_criteria = set().union(*story_criteria.values()) - contract_ids if story_criteria else set()
        if unknown_story_criteria:
            failures.append(
                f"story_trace: stories reference unknown contract criteria {sorted(unknown_story_criteria)}"
            )
    for view_path in sorted((project / "docs" / "views").glob("*.json")) if (project / "docs" / "views").is_dir() else []:
        view = load_json(view_path, failures)
        reference = view.get("story_ref")
        if not isinstance(reference, str) or not reference:
            failures.append(f"story_trace: view {view_path.name} requires a story_ref")
        elif reference not in story_ids:
            failures.append(f"story_trace: view {view_path.name} references unknown story {reference!r}")
    issues_path = project / "issues-manifest.json"
    if issues_path.is_file():
        issues = load_json(issues_path, failures)
        issues_by_id = {
            item.get("id"): item for item in issues.get("issues", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        for issue in issues.get("issues", []) if isinstance(issues.get("issues"), list) else []:
            if not isinstance(issue, dict):
                continue
            direct_refs = issue.get("story_refs", [])
            enabler_refs = issue.get("technical_enabler_for", [])
            refs = set(direct_refs if isinstance(direct_refs, list) else []) | set(
                enabler_refs if isinstance(enabler_refs, list) else []
            )
            if not refs:
                failures.append(
                    f"story_trace: issue {issue.get('id')} requires story_refs or technical_enabler_for"
                )
            unknown = refs - story_ids
            if unknown:
                failures.append(f"story_trace: issue {issue.get('id')} has unknown story refs {sorted(unknown)}")
            allowed_criteria = set().union(*(story_criteria.get(ref, set()) for ref in refs)) if refs else set()
            unknown_criteria = set(issue.get("criterion_refs", [])) - allowed_criteria
            if unknown_criteria:
                failures.append(
                    f"story_trace: issue {issue.get('id')} has criteria outside its referenced stories {sorted(unknown_criteria)}"
                )
        iteration_path = project / "iteration-contract.json"
        if iteration_path.is_file():
            iteration = load_json(iteration_path, failures)
            issue = issues_by_id.get(iteration.get("issue_id"))
            if issue is not None:
                if iteration.get("pbs_leaf") != issue.get("pbs_leaf"):
                    failures.append("story_trace: iteration pbs_leaf does not match its issue")
                issue_refs = set(issue.get("story_refs", [])) | set(issue.get("technical_enabler_for", []))
                if set(iteration.get("story_refs", [])) != issue_refs:
                    failures.append("story_trace: iteration story refs do not match its issue")
                if set(iteration.get("criterion_refs", [])) != set(issue.get("criterion_refs", [])):
                    failures.append("story_trace: iteration criterion refs do not match its issue")
        evidence_path = project / "build-evidence.json"
        if evidence_path.is_file():
            evidence = load_json(evidence_path, failures)
            if evidence.get("status") == "complete":
                issue = issues_by_id.get(evidence.get("issue_id"))
                if issue is not None and evidence.get("pbs_leaf") != issue.get("pbs_leaf"):
                    failures.append("story_trace: build evidence pbs_leaf does not match its issue")
                evidence_criteria = evidence.get("criteria", []) if isinstance(evidence.get("criteria"), list) else []
                evidence_ids = {
                    criterion.get("id") for criterion in evidence_criteria
                    if isinstance(criterion, dict) and isinstance(criterion.get("id"), str)
                }
                expected_ids = set(issue.get("criterion_refs", [])) if issue is not None else set()
                if evidence_ids != expected_ids:
                    failures.append(
                        "story_trace: completed build evidence does not cover issue criteria "
                        f"(expected {sorted(expected_ids)}, got {sorted(evidence_ids)})"
                    )
                for criterion in evidence_criteria:
                    if not isinstance(criterion, dict) or not isinstance(criterion.get("evidence_ref"), str):
                        failures.append("story_trace: every completed criterion requires test or trace evidence")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    failures = check(args.project.resolve())
    if failures:
        print("[story-trace] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[story-trace] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
