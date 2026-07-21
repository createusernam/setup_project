#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Compare immutable scaffold contracts and anchors before and after one worker iteration.
# SCOPE: Hash GRACE contracts/block directives/log anchors, inspect new source modules, and emit deterministic integrity evidence.
# DEPENDS: Python standard library, git, iteration-contract.json, and scaffold-integrity.schema.json.
# END_MODULE_CONTRACT
"""Trusted Phase 6 scaffold integrity checker."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SOURCE_SUFFIXES = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt",
    ".swift", ".c", ".h", ".cpp", ".cs", ".php", ".scala", ".py", ".rb", ".sh",
    ".bash", ".sql", ".lua",
}
CONTROL_PATHS = {"iteration-contract.json", "iteration-budget.json", "scaffold-integrity.json"}

__all__ = ("build_report",)

# START_CONTRACT: build_report
# PURPOSE: Derive immutable scaffold-anchor integrity evidence for one iteration.
# PRE: A committed ready iteration contract names scaffold files and a baseline.
# POST: Returns a deterministic integrity report without modifying source files.
# END_CONTRACT: build_report
MODULE_RE = re.compile(r"(?ms)^.*START_MODULE_CONTRACT.*?$.*?^.*END_MODULE_CONTRACT.*?$")
FUNCTION_RE = re.compile(
    r"(?ms)^.*START_CONTRACT:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$.*?^.*END_CONTRACT:\s*\1\s*$"
)
BLOCK_RE = re.compile(r"(?ms)^.*START_BLOCK_([A-Za-z0-9_]+)\s*$.*?^.*END_BLOCK_\1\s*$")
LOG_RE = re.compile(r"\[[^]\n]+\]\[[^]\n]+\]\[[^]\n]+\]")


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def scaffold_projection(text: str) -> dict[str, Any]:
    module_match = MODULE_RE.search(text)
    module = module_match.group(0) if module_match else None
    functions = [[match.group(1), match.group(0)] for match in FUNCTION_RE.finditer(text)]
    blocks: list[list[Any]] = []
    for match in BLOCK_RE.finditer(text):
        payload = [
            line.strip() for line in match.group(0).splitlines()
            if "START_BLOCK_" in line or "IMPL:" in line or "END_BLOCK_" in line
        ]
        blocks.append([match.group(1), payload])
    return {"module": module, "functions": functions, "blocks": blocks, "logs": LOG_RE.findall(text)}


def anchor_hashes(text: str, path: str) -> dict[str, str]:
    projection = scaffold_projection(text)
    result: dict[str, str] = {}
    if projection["module"] is not None:
        result[f"{path}#MODULE_CONTRACT"] = digest(projection["module"])
    for name, contract in projection["functions"]:
        result[f"{path}#FUNCTION_CONTRACT:{name}"] = digest(contract)
    for name, payload in projection["blocks"]:
        result[f"{path}#BLOCK:{name}"] = digest(payload)
    result[f"{path}#LOG_ANCHORS"] = digest(projection["logs"])
    result[f"{path}#SCAFFOLD_STRUCTURE"] = digest(projection)
    return result


def git(project: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def baseline_text(project: Path, baseline: str, path: str) -> str:
    return git(project, "show", f"{baseline}:{path}")


def load_contract(project: Path, *, require_ready: bool = True) -> dict[str, Any]:
    try:
        document = json.loads((project / "iteration-contract.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read iteration-contract.json: {error}") from error
    if not isinstance(document, dict) or (require_ready and document.get("status") != "ready"):
        raise ValueError("iteration-contract.json must be an object" + (" with status ready" if require_ready else ""))
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


def snapshot_current(project: Path, contract: dict[str, Any]) -> dict[str, str]:
    scaffold_files = contract.get("scaffold_files")
    if not isinstance(scaffold_files, list) or not scaffold_files:
        raise ValueError("scaffold_files must select at least one file")
    result: dict[str, str] = {}
    for path in sorted(scaffold_files):
        source = project / path
        if not source.is_file():
            raise ValueError(f"missing scaffold file: {path}")
        result.update(anchor_hashes(source.read_text(encoding="utf-8", errors="replace"), path))
    return result


def changed_source_paths(project: Path, baseline: str) -> list[str]:
    tracked = {
        path for path in git(project, "diff", "--name-only", "-z", baseline, "--").split("\0") if path
    }
    untracked = {
        path for path in git(project, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if path
    }
    return sorted(
        path for path in (tracked | untracked) - CONTROL_PATHS
        if not path.startswith(".build-loop/") and Path(path).suffix.lower() in SOURCE_SUFFIXES
    )


def add_violation(violations: list[dict[str, str]], path: str, kind: str, anchor: str) -> None:
    item = {"path": path, "type": kind, "anchor": anchor}
    if item not in violations:
        violations.append(item)


def compare_file(
    path: str,
    baseline_projection: dict[str, Any],
    current_projection: dict[str, Any],
    violations: list[dict[str, str]],
) -> None:
    if baseline_projection["module"] != current_projection["module"]:
        add_violation(violations, path, "module_contract_changed", "MODULE_CONTRACT")
    baseline_functions = {name: value for name, value in baseline_projection["functions"]}
    current_functions = {name: value for name, value in current_projection["functions"]}
    for name in sorted(set(baseline_functions) | set(current_functions)):
        if baseline_functions.get(name) != current_functions.get(name):
            add_violation(violations, path, "function_contract_changed", f"FUNCTION_CONTRACT:{name}")
    baseline_blocks = {name: value for name, value in baseline_projection["blocks"]}
    current_blocks = {name: value for name, value in current_projection["blocks"]}
    for name in sorted(set(baseline_blocks) | set(current_blocks)):
        if baseline_blocks.get(name) != current_blocks.get(name):
            add_violation(violations, path, "block_anchor_changed", f"BLOCK:{name}")
            if name in baseline_blocks and name in current_blocks:
                old_impl = [line for line in baseline_blocks[name] if "IMPL:" in line]
                new_impl = [line for line in current_blocks[name] if "IMPL:" in line]
                if old_impl != new_impl:
                    add_violation(violations, path, "impl_directive_changed", f"BLOCK:{name}:IMPL")
    if baseline_projection["logs"] != current_projection["logs"]:
        add_violation(violations, path, "log_anchor_changed", "LOG_ANCHORS")
    if baseline_projection != current_projection:
        add_violation(violations, path, "scaffold_structure_changed", "SCAFFOLD_STRUCTURE")


def build_report(project: Path, contract: dict[str, Any]) -> dict[str, Any]:
    verify_committed_contract(project)
    baseline = contract.get("baseline_commit")
    if not isinstance(baseline, str):
        raise ValueError("baseline_commit must be a git commit ID")
    git(project, "cat-file", "-e", f"{baseline}^{{commit}}")
    scaffold_files = contract.get("scaffold_files")
    declared_hashes = contract.get("contract_anchor_hashes")
    if not isinstance(scaffold_files, list) or not isinstance(declared_hashes, dict):
        raise ValueError("scaffold_files and contract_anchor_hashes are required")
    baseline_hashes: dict[str, str] = {}
    current_hashes: dict[str, str] = {}
    violations: list[dict[str, str]] = []
    for path in sorted(scaffold_files):
        try:
            before = baseline_text(project, baseline, path)
        except ValueError:
            add_violation(violations, path, "original_hash_mismatch", "baseline file")
            continue
        before_projection = scaffold_projection(before)
        baseline_hashes.update(anchor_hashes(before, path))
        current_path = project / path
        if not current_path.is_file():
            add_violation(violations, path, "scaffold_file_missing", "file")
            continue
        current = current_path.read_text(encoding="utf-8", errors="replace")
        current_projection = scaffold_projection(current)
        current_hashes.update(anchor_hashes(current, path))
        compare_file(path, before_projection, current_projection, violations)

    for key in sorted(set(declared_hashes) | set(baseline_hashes)):
        if declared_hashes.get(key) != baseline_hashes.get(key):
            path, _, anchor = key.partition("#")
            add_violation(violations, path or "iteration-contract.json", "original_hash_mismatch", anchor or key)

    scaffold_set = set(scaffold_files)
    for path in changed_source_paths(project, baseline):
        if path in scaffold_set or not (project / path).is_file():
            continue
        text = (project / path).read_text(encoding="utf-8", errors="replace")
        if scaffold_projection(text)["module"] is None:
            add_violation(violations, path, "new_file_missing_module_contract", "MODULE_CONTRACT")

    violations.sort(key=lambda item: (item["path"], item["type"], item["anchor"]))
    gap_kinds = {"original_hash_mismatch", "impl_directive_changed"}
    if any(item["type"] in gap_kinds for item in violations):
        verdict = "CONTRACT_GAP"
        gap: dict[str, str] | None = {
            "type": "architecture_gap", "owning_phase": "5.5",
            "reason": "The scaffold contract or IMPL directive must be corrected and re-attested upstream.",
        }
    elif violations:
        verdict = "SCAFFOLD_DRIFT"
        gap = None
    else:
        verdict = "PASS"
        gap = None
    return {
        "$schema": "./scaffold-integrity.schema.json", "version": "1",
        "producer": "trusted-scaffold-integrity-checker",
        "consumers": ["phase6-semantic-validator", "architect-review", "iteration-dashboard-renderer"],
        "issue_id": contract["issue_id"], "pbs_leaf": contract["pbs_leaf"],
        "baseline_commit": baseline, "verdict": verdict,
        "baseline_anchor_hashes": baseline_hashes, "current_anchor_hashes": current_hashes,
        "violations": violations, "gap": gap,
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    spec = importlib.util.spec_from_file_location("integrity_json_schema", ROOT / "scripts" / "json_schema.py")
    if spec is None or spec.loader is None:
        return ["cannot load trusted JSON Schema validator"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = json.loads((ROOT / "templates" / "project" / "scaffold-integrity.schema.json").read_text(encoding="utf-8"))
    return module.validate(report, schema)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("scaffold-integrity.json"))
    parser.add_argument("--snapshot", action="store_true", help="print current scaffold anchor hashes for a draft iteration contract")
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output if args.output.is_absolute() else project / args.output
    try:
        if args.snapshot:
            print(json.dumps(snapshot_current(project, load_contract(project, require_ready=False)), indent=2, sort_keys=True))
            return 0
        report = build_report(project, load_contract(project))
        errors = validate_report(report)
    except (KeyError, OSError, ValueError) as error:
        print(f"[scaffold-integrity] ERROR: {error}")
        return 1
    if errors:
        print("[scaffold-integrity] ERROR: generated report failed schema validation")
        for error in errors:
            print(f"- {error}")
        return 1
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[scaffold-integrity] {report['verdict']}")
    return {"PASS": 0, "CONTRACT_GAP": 4, "SCAFFOLD_DRIFT": 5}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
