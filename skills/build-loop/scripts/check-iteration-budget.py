#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Measure a worker diff against its canonical one-leaf scope and hard machine budget.
# SCOPE: Read git state and iteration-contract.json, classify changed files, and write deterministic iteration-budget.json.
# DEPENDS: Python standard library, git, iteration-contract.json, and iteration-budget.schema.json.
# END_MODULE_CONTRACT
"""Trusted Phase 6 scope and diff-budget checker."""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONTROL_PATHS = {
    "iteration-contract.json", "iteration-budget.json", "scaffold-integrity.json",
    "iteration-review.json", "iteration-dashboard.json", "build-evidence.json", "dashboard.md",
}
CONTROL_PATTERNS = (".build-loop/*", "iterations/*/dashboard.md", "docs/views/iteration-*.json")
CATEGORIES = ("production", "tests", "docs", "generated", "vendor", "lock")

__all__ = ("build_report",)

# START_CONTRACT: build_report
# PURPOSE: Derive the trusted one-leaf budget report from the worker diff.
# PRE: The committed ready iteration contract names an accessible baseline commit.
# POST: Returns a schema-valid report without modifying the project.
# END_CONTRACT: build_report
LEAF_PATTERN = re.compile(r"\bPBS_LEAF\s*:\s*([A-Za-z0-9_.-]+)")
PUBLIC_INTERFACE_PATTERNS = (
    re.compile(r"^\s*(?:async\s+)?def\s+(?!_)[A-Za-z][A-Za-z0-9_]*\s*\("),
    re.compile(r"^\s*class\s+(?!_)[A-Za-z][A-Za-z0-9_]*\b"),
    re.compile(r"^\s*(?:export\s+|public\s+)(?:async\s+)?(?:class|interface|type|function|const|let|var)\b"),
)


def git(project: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=project, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def load_contract(project: Path) -> dict[str, Any]:
    path = project / "iteration-contract.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read iteration-contract.json: {error}") from error
    if not isinstance(document, dict) or document.get("status") != "ready":
        raise ValueError("iteration-contract.json must be a ready object")
    return document


def verify_committed_contract(project: Path) -> None:
    try:
        committed = git(project, "show", "HEAD:iteration-contract.json")
    except ValueError as error:
        raise ValueError("iteration-contract.json must be committed at HEAD before measurement") from error
    if (project / "iteration-contract.json").read_text(encoding="utf-8") != committed:
        raise ValueError(
            "iteration-contract.json differs from its committed HEAD version; "
            "iteration authority may only change through Phase 5.5 re-attestation"
        )


def is_control_path(path: str) -> bool:
    return path in CONTROL_PATHS or any(
        fnmatch.fnmatchcase(path, pattern) for pattern in CONTROL_PATTERNS
    )


def changed_paths(project: Path, baseline: str) -> tuple[list[str], set[str]]:
    git(project, "cat-file", "-e", f"{baseline}^{{commit}}")
    tracked = {
        path for path in git(project, "diff", "--name-only", "-z", baseline, "--").split("\0") if path
    }
    untracked = {
        path for path in git(project, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if path
    }
    paths = sorted(path for path in tracked | untracked if not is_control_path(path))
    return paths, untracked


def line_counts(project: Path, baseline: str, path: str, untracked: set[str]) -> tuple[int, int]:
    if path in untracked:
        try:
            return len((project / path).read_text(encoding="utf-8", errors="replace").splitlines()), 0
        except OSError as error:
            raise ValueError(f"cannot read untracked path {path}: {error}") from error
    output = git(project, "diff", "--numstat", baseline, "--", path).strip()
    if not output:
        return 0, 0
    added, deleted, _ = output.split("\t", 2)
    if added == "-" or deleted == "-":
        return 0, 0
    return int(added), int(deleted)


def added_lines(project: Path, baseline: str, path: str, untracked: set[str]) -> list[str]:
    if path in untracked:
        return (project / path).read_text(encoding="utf-8", errors="replace").splitlines()
    patch = git(project, "diff", "--unified=0", baseline, "--", path)
    return [line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")]


def category(path: str) -> str:
    pure = PurePosixPath(path)
    parts = set(pure.parts)
    name = pure.name.lower()
    if name.endswith(".lock") or name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "cargo.lock"}:
        return "lock"
    if parts & {"vendor", "vendors", "node_modules", "third_party", "third-party"}:
        return "vendor"
    if path == "docs/agent/PIPELINE-MACHINE.md" or path.startswith("docs/views/") or parts & {"generated", "dist"}:
        return "generated"
    if "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "tests"
    if "docs" in parts or pure.suffix.lower() in {".md", ".mdx", ".rst", ".adoc"}:
        return "docs"
    return "production"


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def budget_metric(actual: int, target: int, maximum: int) -> dict[str, Any]:
    return {
        "actual": actual,
        "target": target,
        "max": maximum,
        "target_exceeded": actual > target,
        "hard_max_exceeded": actual > maximum,
    }


def build_report(project: Path, contract: dict[str, Any]) -> dict[str, Any]:
    verify_committed_contract(project)
    baseline = contract.get("baseline_commit")
    if not isinstance(baseline, str):
        raise ValueError("baseline_commit must be a git commit ID")
    paths, untracked = changed_paths(project, baseline)
    metrics = {
        name: {"files": 0, "added": 0, "deleted": 0, "changed_loc": 0}
        for name in CATEGORIES
    }
    changed_files: list[dict[str, Any]] = []
    selected_leaf = contract.get("pbs_leaf")
    observed_leaves: set[str] = {selected_leaf} if isinstance(selected_leaf, str) else set()
    public_interfaces = 0
    for path in paths:
        added, deleted = line_counts(project, baseline, path, untracked)
        bucket = category(path)
        changed_loc = added + deleted
        changed_files.append({
            "path": path, "category": bucket, "added": added,
            "deleted": deleted, "changed_loc": changed_loc,
        })
        metrics[bucket]["files"] += 1
        metrics[bucket]["added"] += added
        metrics[bucket]["deleted"] += deleted
        metrics[bucket]["changed_loc"] += changed_loc
        lines = added_lines(project, baseline, path, untracked)
        for line in lines:
            observed_leaves.update(LEAF_PATTERN.findall(line))
            if bucket == "production" and any(pattern.search(line) for pattern in PUBLIC_INTERFACE_PATTERNS):
                public_interfaces += 1

    production_loc = metrics["production"]["changed_loc"]
    total_loc = sum(metrics[name]["changed_loc"] for name in ("production", "tests", "docs"))
    budget = {
        "production_loc": budget_metric(production_loc, contract["production_loc_target"], contract["production_loc_max"]),
        "total_loc": budget_metric(total_loc, contract["total_loc_target"], contract["total_loc_max"]),
        "files": budget_metric(len(changed_files), contract["files_target"], contract["max_files"]),
        "public_interfaces": budget_metric(public_interfaces, contract["public_interfaces_target"], contract["max_public_interfaces"]),
    }
    allowed = contract.get("allowed_paths", [])
    forbidden = contract.get("forbidden_paths", [])
    scope_breaches = sorted(
        path for path in paths
        if not matches(path, allowed) or matches(path, forbidden)
    )
    split_reasons: list[str] = []
    if len(observed_leaves) > 1:
        split_reasons.append("multiple_pbs_leaves")
    for name, reason in (
        ("production_loc", "production_loc_max"),
        ("total_loc", "total_loc_max"),
        ("files", "max_files"),
        ("public_interfaces", "max_public_interfaces"),
    ):
        if budget[name]["hard_max_exceeded"]:
            split_reasons.append(reason)
    verdict = "SCOPE_BREACH" if scope_breaches else "SPLIT_REQUIRED" if split_reasons else "PASS"
    return {
        "$schema": "./iteration-budget.schema.json",
        "version": "1",
        "producer": "trusted-iteration-budget-checker",
        "consumers": ["phase6-semantic-validator", "iteration-dashboard-renderer"],
        "issue_id": contract["issue_id"],
        "pbs_leaf": selected_leaf,
        "baseline_commit": baseline,
        "verdict": verdict,
        "changed_files": changed_files,
        "observed_pbs_leaves": sorted(observed_leaves),
        "metrics": metrics,
        "budget": budget,
        "scope_breaches": scope_breaches,
        "split_reasons": split_reasons,
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    module_path = ROOT / "scripts" / "json_schema.py"
    spec = importlib.util.spec_from_file_location("budget_json_schema", module_path)
    if spec is None or spec.loader is None:
        return ["cannot load trusted JSON Schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = json.loads((ROOT / "templates" / "project" / "iteration-budget.schema.json").read_text(encoding="utf-8"))
    return module.validate(report, schema)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("iteration-budget.json"))
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output if args.output.is_absolute() else project / args.output
    try:
        report = build_report(project, load_contract(project))
        errors = validate_report(report)
    except (KeyError, OSError, ValueError) as error:
        print(f"[iteration-budget] ERROR: {error}")
        return 1
    if errors:
        print("[iteration-budget] ERROR: generated report failed schema validation")
        for error in errors:
            print(f"- {error}")
        return 1
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[iteration-budget] {report['verdict']}")
    return {"PASS": 0, "SPLIT_REQUIRED": 2, "SCOPE_BREACH": 3}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
