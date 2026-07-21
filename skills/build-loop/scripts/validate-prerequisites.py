#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Fail closed on build-loop contract prerequisites before mutable loop state is created.
# SCOPE: Validate contract semantics and attestations that are independent of runtime capability probes.
# DEPENDS: Python standard library and project contract artifacts.
# END_MODULE_CONTRACT
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


__all__ = ("validate",)

# START_CONTRACT: validate
# PURPOSE: Verify immutable build-loop prerequisites before mutable loop state exists.
# PRE: The project root is readable.
# POST: Returns every static prerequisite failure without modifying project state.
# END_CONTRACT: validate


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(project: Path) -> list[str]:
    errors: list[str] = []
    contract_path = project / "contract.json"
    attestation_path = project / ".contract-attestation"
    iteration_path = project / "iteration-contract.json"
    if not contract_path.is_file():
        return ["contract.json is missing"]
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"contract.json is unreadable: {exc}"]
    if not attestation_path.is_file() or attestation_path.read_text(encoding="utf-8").strip() != digest(contract_path):
        errors.append(".contract-attestation is missing or does not match contract.json")

    criteria = contract.get("criteria")
    if not isinstance(criteria, list) or len(criteria) < 10:
        errors.append("contract.json must contain at least 10 criteria")
    else:
        for criterion in criteria:
            if not isinstance(criterion, dict):
                errors.append("every criterion must be an object")
                continue
            verify = criterion.get("verify")
            if criterion.get("must_pass") is True and isinstance(verify, dict) and verify.get("method") == "manual":
                errors.append(f"must-pass criterion {criterion.get('id', '<unknown>')} cannot use manual verification")

    is_frontend = contract.get("is_frontend") is True
    is_backend = contract.get("is_backend") is True
    if is_frontend:
        primary = contract.get("user_flow", {}).get("primary_path")
        if not isinstance(primary, list) or not primary:
            errors.append("frontend contract requires a non-empty user_flow.primary_path")
        design = project / "design-contract.json"
        design_attestation = project / ".design-contract-attestation"
        if not design.is_file() or not design_attestation.is_file() or design_attestation.read_text(encoding="utf-8").strip() != digest(design):
            errors.append("frontend contract requires an attested design-contract.json")

    if is_frontend or is_backend:
        integrations = contract.get("integrations", {})
        if not isinstance(integrations, dict):
            errors.append("contract integrations must be an object")
            integrations = {}
        if not isinstance(integrations.get("data_flow"), str) or not integrations["data_flow"].strip():
            errors.append("frontend/backend contract requires integrations.data_flow")
        calls = integrations.get("frontend_calls")
        endpoints = integrations.get("backend_endpoints")
        if not (isinstance(calls, list) and calls) and not (isinstance(endpoints, list) and endpoints):
            errors.append("frontend/backend contract requires a frontend call or backend endpoint")

    if not iteration_path.is_file():
        errors.append("iteration-contract.json is missing")
    else:
        try:
            iteration = json.loads(iteration_path.read_text(encoding="utf-8"))
            if iteration.get("status") != "ready":
                errors.append("iteration-contract.json status must be ready")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"iteration-contract.json is unreadable: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    parser.add_argument("--print-scaffold-files", action="store_true")
    args = parser.parse_args()
    errors = validate(Path(args.project).resolve())
    if errors:
        print("[build-loop] HALT — preconditions failed:")
        for error in errors:
            print(f"  ✗ {error}")
        return 1
    if args.print_scaffold_files:
        iteration = json.loads((Path(args.project).resolve() / "iteration-contract.json").read_text(encoding="utf-8"))
        for path in iteration.get("scaffold_files", []):
            print(path)
    else:
        print("[build-loop] static prerequisites PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
