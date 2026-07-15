#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Evaluate one pipeline transition against the canonical machine contract and project ledger.
# SCOPE: Risk policy, artifact attestation, semantic JSON outcomes, invalidation, model availability, and human gates.
# DEPENDS: Python standard library, pipeline-machine.json, model-routing.json, project model-bindings.json and .pipeline-state.json.
# END_MODULE_CONTRACT
"""Fail-closed transition evaluator for the setup pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


KNOWN_RUNTIMES = {"claude", "codex", "opencode", "api", "manual", "self-hosted"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pointer(document: Any, value: str) -> Any:
    current = document
    if value in {"", "/"}:
        return current
    for raw in value.lstrip("/").split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(key)]
        elif isinstance(current, dict) and key in current:
            current = current[key]
        else:
            raise KeyError(value)
    return current


def applicable(requirement: dict[str, Any], tier: str) -> bool:
    return tier in requirement.get("tiers", ["T0", "T1", "T2", "T3", "T4"])


def valid_runtime(value: Any) -> bool:
    if value in KNOWN_RUNTIMES:
        return True
    if not isinstance(value, str) or not value.startswith("custom:"):
        return False
    slug = value[7:]
    return bool(slug) and slug[0].isalnum() and all(char.islower() or char.isdigit() or char in "._-" for char in slug)


def resolve_binding(bindings: dict[str, Any], profile: str) -> tuple[str, str] | None:
    entry = bindings.get(profile, {})
    if not isinstance(entry, dict) or entry.get("enabled") is not True:
        return None
    runtime = entry.get("runtime")
    model_id = entry.get("model_id")
    if not valid_runtime(runtime) or not isinstance(model_id, str) or not model_id or any(char.isspace() for char in model_id):
        return None
    return runtime, model_id


def evaluate(root: Path, project: Path, phase: str) -> tuple[list[str], list[str], dict[str, Any]]:
    machine = json.loads((root / "pipeline-machine.json").read_text(encoding="utf-8"))
    routing = json.loads((root / "model-routing.json").read_text(encoding="utf-8"))
    transition = machine.get("transitions", {}).get(phase)
    if not transition:
        return [f"phase '{phase}' unknown"], [], {}

    ledger_path = project / ".pipeline-state.json"
    if not ledger_path.is_file():
        if phase != "-1":
            return [f"no ledger at {ledger_path}"], [], transition
        ledger: dict[str, Any] = {"model_bindings_file": "model-bindings.json", "artifacts": {}, "human_gates": {}, "policy": {"risk_tier": machine["risk_policy"]["default"], "skipped_gates": []}}
    else:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    failures: list[str] = []
    warnings: list[str] = []
    policy = ledger.get("policy", {})
    tier = policy.get("risk_tier")
    if tier not in machine["risk_policy"]["tiers"]:
        failures.append("policy.risk_tier must be explicitly set to T0, T1, T2, T3, or T4")
        tier = machine["risk_policy"]["default"]
    if tier not in transition.get("tiers", []):
        failures.append(f"policy: phase {phase} is not on the {tier} route")

    route = routing.get("phases", {}).get(phase, {})
    binding_path = project / ledger.get("model_bindings_file", "model-bindings.json")
    bindings: dict[str, Any] = {}
    if not binding_path.is_file():
        failures.append(f"model: binding file missing at {binding_path}")
    else:
        try:
            binding_document = json.loads(binding_path.read_text(encoding="utf-8"))
            if binding_document.get("version") != "1":
                failures.append("model: binding file version must be '1'")
            bindings = binding_document.get("bindings", {})
            if not isinstance(bindings, dict):
                failures.append("model: bindings must be an object")
                bindings = {}
            unknown_profiles = sorted(set(bindings) - set(routing.get("profiles", {})))
            if unknown_profiles:
                failures.append(f"model: unknown capability profiles: {', '.join(unknown_profiles)}")
        except (json.JSONDecodeError, AttributeError) as error:
            failures.append(f"model: cannot read bindings at {binding_path}: {error}")

    resolved: dict[str, str] = {}
    required_profile = route.get("profile", "")
    if required_profile:
        binding = resolve_binding(bindings, required_profile)
        if binding is None:
            failures.append(f"model: capability profile {required_profile!r} is unbound or disabled")
        else:
            resolved["primary"] = binding[1]
    for role, profile in route.get("roles", {}).items():
        binding = resolve_binding(bindings, profile)
        if binding is None:
            failures.append(f"model: role {role!r} capability profile {profile!r} is unbound or disabled")
        else:
            resolved[role] = binding[1]
    for group in route.get("distinct_roles", []):
        values = [resolved.get(role) for role in group]
        if None not in values and len(set(values)) != len(values):
            failures.append(f"collegium: roles {group} must resolve to different model IDs, got {values}")

    records = ledger.get("artifacts", {})
    for requirement in transition.get("requires", []):
        if not applicable(requirement, tier):
            continue
        name = requirement["artifact"]
        artifact = project / name
        record = records.get(name, {}) if isinstance(records.get(name, {}), dict) else {}
        if not artifact.exists():
            failures.append(f"input: required artifact {name!r} missing")
            continue
        if record.get("status") == "invalidated" or record.get("invalidated_by"):
            failures.append(f"input: {name!r} is invalidated by {record.get('invalidated_by', 'ledger status')}")
        if requirement.get("attested"):
            expected = record.get("sha256")
            if not expected:
                failures.append(f"input: {name!r} has no sha256 attestation in the ledger")
            else:
                actual = sha256(artifact)
                if actual != expected:
                    failures.append(f"input: {name!r} changed since attested (ledger {expected[:12]}…, actual {actual[:12]}…)")
        if "json_pointer" in requirement:
            try:
                document = json.loads(artifact.read_text(encoding="utf-8"))
                actual_value = pointer(document, requirement["json_pointer"])
            except (json.JSONDecodeError, KeyError, IndexError, ValueError) as error:
                failures.append(f"semantic: cannot read {name}{requirement['json_pointer']}: {error}")
                continue
            if "equals" in requirement and actual_value != requirement["equals"]:
                failures.append(f"semantic: {name}{requirement['json_pointer']} must equal {requirement['equals']!r}, got {actual_value!r}")
            if "in" in requirement and actual_value not in requirement["in"]:
                failures.append(f"semantic: {name}{requirement['json_pointer']} must be one of {requirement['in']!r}, got {actual_value!r}")

    human_gate = transition.get("human_gate")
    if human_gate:
        signature = ledger.get("human_gates", {}).get(human_gate, {})
        if not all(signature.get(key) for key in ("by", "at")):
            failures.append(f"human_gate: {human_gate!r} requires by and at")

    if tier in {"T3", "T4"} and phase not in machine["risk_policy"]["tiers"][tier]["required_phases"]:
        warnings.append(f"phase {phase} is outside the canonical {tier} route")
    return failures, warnings, {**transition, "tier": tier, "required_profile": required_profile, "resolved_models": resolved}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", help="pipeline phase, for example 4c or 6")
    parser.add_argument("project_dir", nargs="?", default=".")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    failures, warnings, transition = evaluate(args.root.resolve(), Path(args.project_dir).resolve(), args.phase)
    print(f"=== preflight · phase {args.phase} · {transition.get('skill', '?')} · {transition.get('tier', '?')} ===")
    for warning in warnings:
        print(f"WARN: {warning}")
    if failures:
        print("HALT — preconditions failed:")
        for failure in failures:
            print(f"  ✗ {failure}")
        return 1
    print("✓ policy ✓ models ✓ semantic inputs/attestations ✓ human gate")
    print(f"required profile: {transition.get('required_profile', '')}; resolved models: {transition.get('resolved_models', {})}")
    print("agent must confirm its running runtime/model matches the resolved binding for its role")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
