#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Evaluate one pipeline transition against the canonical machine contract and project ledger.
# SCOPE: Risk policy, artifact attestation, semantic JSON outcomes, invalidation, model availability, and human gates.
# DEPENDS: Python standard library, pipeline-machine.json, model-routing.json, project model-bindings.json and .pipeline-state.json.
# END_MODULE_CONTRACT
"""Fail-closed transition evaluator for the setup pipeline."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


KNOWN_RUNTIMES = {"claude", "codex", "opencode", "api", "manual", "self-hosted"}
SHA256 = re.compile(r"^[a-f0-9]{64}$")
SPEC_GAP_GATE_PHASES = {"1", "2", "4"}
LEDGER_STATUSES = {"draft", "ready", "approved", "complete", "invalidated"}
HUMAN_GATES = {"viz_before_tickets", "contract_locked", "human_acceptance"}


def behavior_pack_required(tier: str, conditions: dict[str, Any]) -> bool:
    """Return whether the selected route needs the readable behavior traceability pack."""
    return tier in {"T3", "T4"} or conditions.get("behavior_pack_required") is True


# START_BLOCK_RULE_HELPERS
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_schema_validator(root: Path) -> Any:
    """Load the repository-owned portable JSON Schema validator."""
    path = root / "scripts" / "json_schema.py"
    spec = importlib.util.spec_from_file_location("setup_json_schema", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load JSON Schema validator at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def behavior_pack_errors(root: Path, project: Path) -> list[str]:
    """Run the visualization-owned checker as a Phase 4c/5 policy dependency."""
    path = root / "skills" / "visualization" / "scripts" / "check-behavior-pack.py"
    spec = importlib.util.spec_from_file_location("behavior_pack_checker", path)
    if spec is None or spec.loader is None:
        return ["behavior_pack: cannot load visualization checker"]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check(project, root)


def artifact_contract(machine: dict[str, Any], name: str) -> tuple[str, dict[str, Any]] | None:
    """Resolve registry metadata for an artifact path."""
    for registry_name in ("artifact_contracts", "artifact_owners"):
        for pattern, contract in machine.get(registry_name, {}).items():
            if fnmatch.fnmatch(name, pattern):
                return pattern, contract
    return None


def artifact_schema_errors(root: Path, artifact: Path, name: str, machine: dict[str, Any]) -> list[str]:
    """Validate a registered artifact before its bytes may carry an attestation."""
    resolved = artifact_contract(machine, name)
    if resolved is None:
        return []
    _, contract = resolved
    schema_name = contract.get("schema")
    if not schema_name:
        return []
    schema_path = root / schema_name
    if not schema_path.is_file():
        return [f"schema: registered schema missing for {name!r}: {schema_name}"]
    validator = load_schema_validator(root)
    return [f"schema: {name}: {error}" for error in validator.validate_file(artifact, schema_path)]


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


def condition_matches(rule: dict[str, Any] | None, conditions: dict[str, Any]) -> bool:
    if not rule:
        return True
    return conditions.get(rule.get("condition")) == rule.get("equals")


def applicable(requirement: dict[str, Any], tier: str, conditions: dict[str, Any]) -> bool:
    return tier in requirement.get("tiers", ["T0", "T1", "T2", "T3", "T4"]) and condition_matches(
        requirement.get("when"), conditions
    )


def artifact_semantic_errors(name: str, document: Any, tier: str) -> list[str]:
    """Reject terminal-looking artifacts that contain no usable evidence."""
    if not isinstance(document, dict):
        return [f"semantic: {name} must contain a JSON object"]
    failures: list[str] = []
    if name == "build-evidence.json" and document.get("status") == "complete":
        checks = document.get("checks", [])
        if not checks or any(not isinstance(item, dict) or item.get("status") != "pass" for item in checks):
            failures.append("semantic: complete build-evidence.json requires at least one check and every check status=pass")
        criteria = document.get("criteria", [])
        if tier in {"T2", "T3", "T4"} and not criteria:
            failures.append("semantic: T2–T4 complete build-evidence.json requires criterion evidence")
        if any(not isinstance(item, dict) or item.get("status") != "PASS" for item in criteria):
            failures.append("semantic: complete build-evidence.json requires every criterion status=PASS")
    elif name == "issues-manifest.json" and document.get("status") == "approved":
        if not document.get("issues"):
            failures.append("semantic: approved issues-manifest.json requires at least one issue")
    elif name == "scaffold-manifest.json" and document.get("status") == "ready":
        if not document.get("files"):
            failures.append("semantic: ready scaffold-manifest.json requires at least one scaffolded file")
        checks = document.get("checks", [])
        if not checks or any(not isinstance(item, dict) or item.get("status") != "pass" for item in checks):
            failures.append("semantic: ready scaffold-manifest.json requires at least one passing check and no failures")
    elif name == "risk-review.json" and document.get("verdict") == "PASS":
        risks = document.get("risks", [])
        if not risks:
            failures.append("semantic: PASS risk-review.json requires at least one assessed T4 risk")
        if any(not isinstance(item, dict) or item.get("status") == "open" for item in risks):
            failures.append("semantic: PASS risk-review.json cannot contain open risks")
        if not document.get("rollback", {}).get("defined"):
            failures.append("semantic: PASS risk-review.json requires a defined rollback")
        if document.get("accepted_by") in {None, "", "replace-me"}:
            failures.append("semantic: PASS risk-review.json requires an accountable accepted_by identity")
    elif name == "rollout-plan.json" and document.get("status") in {"ready", "complete"}:
        if not document.get("stages"):
            failures.append("semantic: ready/complete rollout-plan.json requires at least one rollout stage")
        rollback = document.get("rollback", {})
        if not rollback.get("defined"):
            failures.append("semantic: ready/complete rollout-plan.json requires rollback.defined=true")
        for field in ("trigger", "action", "owner"):
            if rollback.get(field) in {None, "", "replace-me"}:
                failures.append(f"semantic: ready/complete rollout-plan.json requires a concrete rollback.{field}")
    return failures


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


def model_conformance_errors(
    root: Path,
    project: Path,
    machine: dict[str, Any],
    profile: str,
    binding: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    """Verify that a required enabled binding is backed by matching executable probe evidence."""
    if not binding.get("enabled") or policy.get("mode", "advisory") != "required":
        return []
    reference = binding.get("conformance_ref")
    if not isinstance(reference, str) or not reference:
        return [f"model_conformance: enabled profile {profile!r} requires conformance_ref"]
    path = (project / reference).resolve()
    try:
        name = path.relative_to(project).as_posix()
    except ValueError:
        return [f"model_conformance: {profile!r} conformance_ref must stay inside the project"]
    if not path.is_file():
        return [f"model_conformance: {profile!r} evidence missing at {path}"]
    failures = artifact_schema_errors(root, path, name, machine)
    if failures:
        return failures
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"model_conformance: cannot read {name}: {error}"]
    summary = document.get("summary", {})
    if profile in {"implementation_general", "implementation_ui"}:
        critical_ids = {
            "bounded_patch", "allowed_path_compliance", "compiler_typecheck_feedback",
            "targeted_test_execution", "scaffold_anchor_preservation", "stop_on_contract_gap",
            "secret_non_disclosure", "destructive_command_refusal",
            "untrusted_repository_instruction_resistance", "schema_valid_handoff_dashboard_input",
            "failure_recovery",
        }
        if document.get("profile") != "coding_worker":
            failures.append(f"model_conformance: {profile!r} requires coding_worker profile evidence")
        critical = {
            item.get("id"): item for item in document.get("scenarios", [])
            if isinstance(item, dict) and item.get("critical") is True and isinstance(item.get("id"), str)
        }
        missing_or_failed = sorted(
            probe_id for probe_id in critical_ids
            if probe_id not in critical or critical[probe_id].get("status") != "pass"
        )
        unknown = sorted(set(critical) - critical_ids)
        if missing_or_failed or unknown:
            detail = []
            if missing_or_failed:
                detail.append("missing/failed: " + ", ".join(missing_or_failed))
            if unknown:
                detail.append("unknown: " + ", ".join(unknown))
            failures.append(f"model_conformance: {profile!r} critical coding probes must pass exactly ({'; '.join(detail)})")
        if summary.get("critical_failures") != [] or summary.get("critical_total") != len(critical_ids):
            failures.append(f"model_conformance: {profile!r} critical summary is inconsistent")
    expected_harness = policy.get("harness_version")
    minimum = policy.get("minimum_pass_rate", 1)
    if document.get("model_id") != binding.get("model_id"):
        failures.append(
            f"model_conformance: {profile!r} evidence model_id {document.get('model_id')!r} "
            f"does not match binding {binding.get('model_id')!r}"
        )
    if expected_harness and document.get("harness_version") != expected_harness:
        failures.append(
            f"model_conformance: {profile!r} requires harness {expected_harness!r}, "
            f"got {document.get('harness_version')!r}"
        )
    if not summary.get("qualified") or not isinstance(summary.get("pass_rate"), (int, float)) or summary["pass_rate"] < minimum:
        failures.append(
            f"model_conformance: {profile!r} pass_rate must be >= {minimum} and qualified=true"
        )
    return failures


def ledger_errors(ledger: Any) -> list[str]:
    """Reject malformed ledger fields that can otherwise weaken an evaluated transition."""
    if not isinstance(ledger, dict):
        return ["ledger: .pipeline-state.json must contain a JSON object"]
    errors: list[str] = []
    if ledger.get("version") != "2":
        errors.append("ledger: version must be '2'")
    if not isinstance(ledger.get("phase"), str) or not ledger.get("phase"):
        errors.append("ledger: phase must be a non-empty machine phase")
    if not isinstance(ledger.get("policy"), dict):
        errors.append("ledger: policy must be an object")
    if not isinstance(ledger.get("artifacts", {}), dict):
        errors.append("ledger: artifacts must be an object")
    if not isinstance(ledger.get("human_gates", {}), dict):
        errors.append("ledger: human_gates must be an object")
    elif set(ledger.get("human_gates", {})) != HUMAN_GATES:
        errors.append("ledger: human_gates must contain exactly contract_locked, viz_before_tickets, and human_acceptance; run setup-pipeline migrate")
    phase_processes = ledger.get("phase_processes", {})
    if not isinstance(phase_processes, dict):
        errors.append("ledger: phase_processes must be an object")
    else:
        for phase, binding in phase_processes.items():
            if not isinstance(phase, str) or not phase:
                errors.append("ledger: every phase_processes key must be a non-empty phase")
            if not isinstance(binding, dict) or set(binding) != {"skill"}:
                errors.append(f"ledger: phase_processes[{phase!r}] must contain exactly skill")
                continue
            skill = binding.get("skill")
            if not isinstance(skill, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", skill):
                errors.append(f"ledger: phase_processes[{phase!r}].skill must be a lowercase skill slug")
    policy = ledger.get("policy", {})
    if isinstance(policy, dict):
        for obsolete in ("skipped_gates", "skip_contract"):
            if obsolete in policy:
                errors.append(f"ledger: obsolete policy.{obsolete} has no authority; run setup-pipeline migrate")
    bindings_file = ledger.get("model_bindings_file", "model-bindings.json")
    if not isinstance(bindings_file, str) or not bindings_file or Path(bindings_file).is_absolute() or ".." in Path(bindings_file).parts:
        errors.append("ledger: model_bindings_file must be a non-empty project-relative path")
    records = ledger.get("artifacts", {})
    if isinstance(records, dict):
        for name, record in records.items():
            if not isinstance(record, dict):
                errors.append(f"ledger: artifact record {name!r} must be an object")
                continue
            digest = record.get("sha256")
            if digest is not None and (not isinstance(digest, str) or not SHA256.fullmatch(digest)):
                errors.append(f"ledger: artifact {name!r} sha256 must be null or a lowercase SHA-256 digest")
            if record.get("status") not in LEDGER_STATUSES:
                errors.append(f"ledger: artifact {name!r} status must be one of {sorted(LEDGER_STATUSES)}")
            if "invalidated_by" not in record or not isinstance(record.get("invalidated_by"), (str, type(None))):
                errors.append(f"ledger: artifact {name!r} invalidated_by must be null or a string")
    return errors


def load_phase_process_descriptor(root: Path, skill: str) -> tuple[Path, dict[str, Any]]:
    """Load a trusted, skill-owned read-only validator without accepting project commands."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", skill):
        raise ValueError("phase-process skill must be a lowercase slug")
    skills_root = (root / "skills").resolve()
    skill_dir = (skills_root / skill).resolve()
    try:
        skill_dir.relative_to(skills_root)
    except ValueError as error:
        raise ValueError("phase-process skill must resolve inside setup skills") from error
    descriptor_path = skill_dir / "pipeline-validator.json"
    if not descriptor_path.is_file():
        raise ValueError(f"skill {skill!r} has no pipeline-validator.json")
    try:
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read phase-process descriptor for {skill!r}: {error}") from error
    if not isinstance(descriptor, dict) or descriptor.get("version") != "1":
        raise ValueError(f"phase-process descriptor for {skill!r} must use version '1'")
    if descriptor.get("runner") != "python" or descriptor.get("read_only") is not True:
        raise ValueError(f"phase-process descriptor for {skill!r} must declare python and read_only=true")
    raw_script = descriptor.get("script")
    if not isinstance(raw_script, str) or not raw_script or Path(raw_script).is_absolute():
        raise ValueError(f"phase-process validator for {skill!r} must be a relative script path")
    script = (skill_dir / raw_script).resolve()
    try:
        script.relative_to(skill_dir)
    except ValueError as error:
        raise ValueError(f"phase-process validator for {skill!r} must stay inside the skill") from error
    if not script.is_file():
        raise ValueError(f"phase-process validator script is missing: {script}")
    arguments = descriptor.get("arguments", [])
    if not isinstance(arguments, list) or any(not isinstance(item, str) for item in arguments):
        raise ValueError(f"phase-process arguments for {skill!r} must be an array of strings")
    timeout = descriptor.get("timeout_seconds", 30)
    if not isinstance(timeout, int) or not 1 <= timeout <= 120:
        raise ValueError(f"phase-process timeout for {skill!r} must be 1..120 seconds")
    failure_next = descriptor.get("failure_next")
    if not isinstance(failure_next, str) or not failure_next.strip():
        raise ValueError(f"phase-process descriptor for {skill!r} requires failure_next")
    return script, descriptor


def phase_process_check(
    root: Path, project: Path, phase: str, ledger: dict[str, Any]
) -> tuple[str | None, list[str], str | None]:
    """Run the validator bound to a phase and return skill, blockers, and recovery action."""
    binding = ledger.get("phase_processes", {}).get(phase)
    if binding is None:
        return None, [], None
    if not isinstance(binding, dict) or not isinstance(binding.get("skill"), str):
        return None, [f"phase_process: malformed binding for phase {phase}"], "repair .pipeline-state.json, then rerun status"
    skill = binding["skill"]
    try:
        script, descriptor = load_phase_process_descriptor(root, skill)
    except ValueError as error:
        return skill, [f"phase_process[{skill}]: {error}"], "install or repair the named phase-process skill, then rerun status"
    arguments = [item.replace("{project}", str(project)) for item in descriptor.get("arguments", [])]
    try:
        result = subprocess.run(
            [sys.executable, str(script), *arguments],
            cwd=project,
            text=True,
            capture_output=True,
            timeout=descriptor.get("timeout_seconds", 30),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return skill, [f"phase_process[{skill}]: validator timed out"], descriptor["failure_next"]
    if result.returncode == 0:
        return skill, [], None
    combined = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    lines = [line.strip() for line in combined.splitlines() if line.strip()][:20]
    failures = [f"phase_process[{skill}]: {line[:500]}" for line in lines]
    if not failures:
        failures = [f"phase_process[{skill}]: validator exited {result.returncode} without diagnostics"]
    return skill, failures, descriptor["failure_next"]


def required_phase_process_errors(
    phase: str, transition: dict[str, Any], ledger: dict[str, Any]
) -> list[str]:
    """Require the machine-declared trusted validator binding for a phase."""
    required = transition.get("phase_process")
    if required is None:
        return []
    binding = ledger.get("phase_processes", {}).get(phase)
    if not isinstance(binding, dict) or binding.get("skill") != required:
        return [f"phase_process: phase {phase} requires trusted skill {required!r}"]
    return []


def specification_gap_errors(document: Any) -> list[str]:
    """Reject unresolved material requirement gaps before planning or contract work."""
    if not isinstance(document, dict):
        return ["specification_gap: evidence-handoff.json must contain an object"]
    gaps = document.get("spec_gaps", [])
    if not isinstance(gaps, list):
        return ["specification_gap: spec_gaps must be an array"]
    failures: list[str] = []
    seen: set[str] = set()
    for index, gap in enumerate(gaps):
        label = f"spec_gaps[{index}]"
        if not isinstance(gap, dict):
            failures.append(f"specification_gap: {label} must be an object")
            continue
        gap_id = gap.get("id")
        if not isinstance(gap_id, str) or not gap_id:
            failures.append(f"specification_gap: {label}.id must be non-empty")
            continue
        if gap_id in seen:
            failures.append(f"specification_gap: duplicate id {gap_id!r}")
        seen.add(gap_id)
        if gap.get("materiality") != "blocking":
            continue
        status = gap.get("status")
        disposition = gap.get("disposition")
        resolution_ref = gap.get("resolution_ref")
        accepted_by = gap.get("accepted_by")
        if status == "open":
            failures.append(f"specification_gap: blocking gap {gap_id!r} is unresolved")
        elif status == "resolved":
            if disposition not in {"answer", "prototype"} or not resolution_ref:
                failures.append(
                    f"specification_gap: resolved blocking gap {gap_id!r} requires answer/prototype disposition and resolution_ref"
                )
        elif status == "accepted":
            if disposition != "accept_risk" or not resolution_ref or not accepted_by:
                failures.append(
                    f"specification_gap: accepted blocking gap {gap_id!r} requires accept_risk, resolution_ref, and accepted_by"
                )
        elif status == "out_of_scope":
            if disposition != "out_of_scope" or not resolution_ref or not accepted_by:
                failures.append(
                    f"specification_gap: out-of-scope blocking gap {gap_id!r} requires out_of_scope, resolution_ref, and accepted_by"
                )
        else:
            failures.append(f"specification_gap: blocking gap {gap_id!r} has invalid status {status!r}")
    return failures


def human_authority_errors(
    root: Path,
    project: Path,
    gate: str,
    tier: str,
    signature: dict[str, Any],
    machine: dict[str, Any],
    ledger: dict[str, Any] | None = None,
) -> tuple[list[str], bool]:
    """Validate configured role assignments without making the optional file mandatory."""
    path = project / "role-assignment.json"
    if not path.is_file():
        return [], False
    schema_failures = artifact_schema_errors(root, path, "role-assignment.json", machine)
    if schema_failures:
        return schema_failures, True
    try:
        assignment = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"human_authority: cannot read role-assignment.json: {error}"], True
    required = {
        "viz_before_tickets": ["technical_owner"],
        "human_acceptance": ["accountable_acceptor"],
        "contract_locked": ["product_owner", "technical_owner"] if tier in {"T3", "T4"} else ["product_owner"],
    }[gate]
    adopted = any(assignment.get(role) for role in ("product_owner", "technical_owner", "accountable_acceptor"))
    if not adopted:
        return [], False
    failures: list[str] = []
    configured = {role: assignment.get(role) for role in required if assignment.get(role)}
    missing_roles = [role for role in required if role not in configured]
    failures.extend(f"human_authority: role-assignment.json requires {role}" for role in missing_roles)
    if ledger is not None:
        record = ledger.get("artifacts", {}).get("role-assignment.json", {})
        if not isinstance(record, dict) or record.get("status") not in {"ready", "approved"}:
            failures.append("human_authority: adopted role-assignment.json must be attested")
        elif record.get("sha256") != sha256(path):
            failures.append("human_authority: role-assignment.json changed since attestation")
    approvals = signature.get("approvals", {}) if isinstance(signature.get("approvals", {}), dict) else {}
    for role, identity in configured.items():
        approval = approvals.get(role, {}) if isinstance(approvals.get(role, {}), dict) else {}
        legacy_match = signature.get("by") == identity and bool(signature.get("at"))
        if not legacy_match and not (approval.get("by") == identity and approval.get("at")):
            failures.append(
                f"human_authority: {gate!r} requires {role} approval by assigned identity {identity!r}"
            )
    return failures, True
# END_BLOCK_RULE_HELPERS


# START_BLOCK_TRANSITION_EVALUATION
def artifact_ownership_errors(
    root: Path, project: Path, phase: str, ledger: dict[str, Any], machine: dict[str, Any]
) -> list[str]:
    """Reject unregistered phase-owned output outside its producer phase.

    Bootstrap templates are allowed while byte-identical to their canonical scaffold. Once changed,
    they become producer output and require the owning phase plus ledger attestation.
    """
    failures: list[str] = []
    records = ledger.get("artifacts", {}) if isinstance(ledger.get("artifacts", {}), dict) else {}
    for pattern, ownership in machine.get("artifact_owners", {}).items():
        owners = ownership.get("producer_phases") or [ownership.get("producer_phase")]
        owners = [owner for owner in owners if owner is not None]
        owner_label = f"phase {owners[0]}" if len(owners) == 1 else f"phases {owners}"
        if not owners or phase in owners:
            continue
        for artifact in project.glob(pattern):
            if not artifact.is_file():
                continue
            name = artifact.relative_to(project).as_posix()
            record = records.get(name, {}) if isinstance(records.get(name, {}), dict) else {}
            recorded_hash = record.get("sha256")
            if recorded_hash:
                if recorded_hash == sha256(artifact):
                    continue
                failures.append(
                    f"artifact_ownership: {name!r} changed outside producer {owner_label}; "
                    f"ledger phase is {phase} and the recorded attestation no longer matches"
                )
                continue
            template_name = ownership.get("template")
            if template_name:
                template = root / template_name
                if template.is_file() and sha256(template) == sha256(artifact):
                    continue
            failures.append(
                f"artifact_ownership: {name!r} belongs to {owner_label}, but ledger phase is {phase}; "
                f"treat it as an unapproved draft and enter one of {owners} before writing or attesting it"
            )
    return failures


def artifact_flow_errors(machine: dict[str, Any]) -> list[str]:
    """Ensure every declared phase output is a checked input downstream.

    Completion requirements count as the terminal consumer for final review artifacts. Keeping this
    invariant executable prevents phases from producing ceremonial files that later work ignores.
    """
    transitions = machine.get("transitions", {})
    phase_position = {phase: index for index, phase in enumerate(transitions)}
    failures: list[str] = []
    for pattern, ownership in machine.get("artifact_owners", {}).items():
        owners = ownership.get("producer_phases") or [ownership.get("producer_phase")]
        owners = [owner for owner in owners if owner is not None]
        consumers: list[str] = []
        for phase, transition in transitions.items():
            requirements = list(transition.get("requires", []))
            requirements.extend(transition.get("completion", {}).get("requires", []))
            if any(requirement.get("artifact") == pattern for requirement in requirements):
                consumers.append(phase)
        if not consumers:
            failures.append(
                f"artifact_flow: output {pattern!r} from phase(s) {owners} has no downstream requirement"
            )
        elif not owners or all(
            owner not in phase_position or all(
                phase_position.get(consumer, -1) < phase_position[owner] for consumer in consumers
            )
            for owner in owners
        ):
            failures.append(
                f"artifact_flow: output {pattern!r} from phase(s) {owners} is only consumed by earlier phases {consumers}"
            )
    return failures


def outcome_contract_errors(machine: dict[str, Any]) -> list[str]:
    """Ensure every typed verdict resolves to exactly one executable continuation."""
    transitions = machine.get("transitions", {})
    failures: list[str] = []
    for phase, transition in transitions.items():
        outcomes = transition.get("outcomes", {})
        if not isinstance(outcomes, dict):
            failures.append(f"outcomes: phase {phase!r} outcomes must be an object")
            continue
        for verdict, outcome in outcomes.items():
            if not isinstance(outcome, dict):
                failures.append(f"outcomes: {phase}/{verdict} must be an object")
                continue
            choices = [key for key in ("next", "return_to", "stop") if key in outcome]
            if len(choices) != 1:
                failures.append(f"outcomes: {phase}/{verdict} must have exactly one of next, return_to, stop")
                continue
            target = outcome.get("next") or outcome.get("return_to")
            if target is not None and target not in transitions:
                failures.append(f"outcomes: {phase}/{verdict} targets unknown phase {target!r}")
            if outcome.get("stop") is not True and target is None:
                failures.append(f"outcomes: {phase}/{verdict} has no target or terminal stop")
    return failures


def human_request_contract_errors(machine: dict[str, Any]) -> list[str]:
    """Fail closed when a machine-emitted human wait lacks an actionable response contract."""
    failures: list[str] = []
    requests = machine.get("human_requests", {})
    required_ids = {"model_bindings", *machine.get("gate_owners", {})}
    missing = sorted(required_ids - set(requests)) if isinstance(requests, dict) else sorted(required_ids)
    for request_id in missing:
        failures.append(f"human_request: missing contract for {request_id!r}")
    if not isinstance(requests, dict):
        return failures

    required_fields = {
        "authority", "question", "why_needed", "evidence_refs", "response",
        "allowed_responses", "consequences", "resume_action",
    }
    for request_id, request in requests.items():
        if not isinstance(request, dict):
            failures.append(f"human_request: {request_id!r} must be an object")
            continue
        for field in sorted(required_fields - set(request)):
            failures.append(f"human_request: {request_id!r} missing {field!r}")
        for field in ("authority", "question", "why_needed", "resume_action"):
            if field in request and (not isinstance(request[field], str) or not request[field].strip()):
                failures.append(f"human_request: {request_id!r}.{field} must be non-empty text")
        if isinstance(request.get("question"), str) and not request["question"].rstrip().endswith("?"):
            failures.append(f"human_request: {request_id!r}.question must be one explicit question")
        for field in ("evidence_refs", "allowed_responses"):
            values = request.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
                failures.append(f"human_request: {request_id!r}.{field} must be a non-empty string list")
        for field in ("evidence_refs", "setup_refs"):
            for value in request.get(field, []) if isinstance(request.get(field, []), list) else []:
                path = Path(value)
                if path.is_absolute() or ".." in path.parts:
                    failures.append(f"human_request: {request_id!r}.{field} path {value!r} must be relative")
        consequences = request.get("consequences")
        if not isinstance(consequences, dict) or not consequences or not all(
            isinstance(key, str) and isinstance(value, str) and value.strip()
            for key, value in consequences.items()
        ):
            failures.append(f"human_request: {request_id!r}.consequences must be a non-empty text map")
        response = request.get("response")
        if not isinstance(response, dict):
            failures.append(f"human_request: {request_id!r} missing valid 'response' object")
            continue
        mode = response.get("mode")
        if mode == "file":
            for field in ("path", "schema"):
                value = response.get(field)
                if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
                    failures.append(f"human_request: {request_id!r}.response.{field} must be a relative path")
        elif mode == "inline":
            if not isinstance(response.get("format"), dict) or not response["format"]:
                failures.append(f"human_request: {request_id!r} inline response requires a format object")
            if not isinstance(response.get("record_command"), str) or not response["record_command"].strip():
                failures.append(f"human_request: {request_id!r} inline response requires a record_command")
        else:
            failures.append(f"human_request: {request_id!r}.response.mode must be file or inline")
    return failures


def evaluate(
    root: Path,
    project: Path,
    phase: str,
    completion: bool = False,
    *,
    ledger_override: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], dict[str, Any]]:
    machine = json.loads((root / "pipeline-machine.json").read_text(encoding="utf-8"))
    routing = json.loads((root / "model-routing.json").read_text(encoding="utf-8"))
    transition = machine.get("transitions", {}).get(phase)
    if not transition:
        return [f"phase '{phase}' unknown"], [], {}

    ledger_path = project / ".pipeline-state.json"
    if ledger_override is not None:
        ledger = ledger_override
    elif not ledger_path.is_file():
        if phase != "-1":
            return [f"no ledger at {ledger_path}"], [], transition
        ledger: dict[str, Any] = {
            "version": "2",
            "phase": "-1",
            "model_bindings_file": "model-bindings.json",
            "artifacts": {},
            "human_gates": {},
            "phase_processes": {},
            "policy": {"risk_tier": None, "conditions": {"research_required": None, "frontend": None}},
        }
    else:
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            return [f"ledger: cannot read {ledger_path}: {error}"], [], transition

    failures: list[str] = ledger_errors(ledger)
    failures.extend(required_phase_process_errors(phase, transition, ledger))
    if ledger_path.is_file():
        validator = load_schema_validator(root)
        ledger_schema = root / "templates" / "project" / "pipeline-state.schema.json"
        failures.extend(
            f"schema: .pipeline-state.json: {error}"
            for error in validator.validate_file(ledger_path, ledger_schema)
        )
    failures.extend(artifact_flow_errors(machine))
    failures.extend(outcome_contract_errors(machine))
    failures.extend(human_request_contract_errors(machine))
    warnings: list[str] = []
    policy = ledger.get("policy", {})
    conditions = policy.get("conditions", {}) if isinstance(policy.get("conditions", {}), dict) else {}
    if ledger.get("phase") != phase:
        failures.append(
            f"ledger: current phase is {ledger.get('phase')!r}, requested {phase!r}; run setup-pipeline enter {phase}"
        )
    failures.extend(artifact_ownership_errors(root, project, phase, ledger, machine))
    tier = policy.get("risk_tier")
    if tier is None and phase in {"-1", "0"}:
        tier = machine["risk_policy"]["default"]
    elif tier not in machine["risk_policy"]["tiers"]:
        failures.append("policy.risk_tier must be explicitly set to T0, T1, T2, T3, or T4")
        tier = machine["risk_policy"]["default"]
    if tier not in transition.get("tiers", []):
        failures.append(f"policy: phase {phase} is not on the {tier} route")
    if tier in {"T2", "T3", "T4"} and phase not in {"-1", "0"}:
        for condition_name in ("research_required", "frontend"):
            if conditions.get(condition_name) is None:
                failures.append(
                    f"policy: condition {condition_name!r} is unclassified; run setup-pipeline set-condition {condition_name} true|false"
                )
    transition_condition = transition.get("when")
    if transition_condition:
        condition_name = transition_condition["condition"]
        if conditions.get(condition_name) is None:
            failures.append(
                f"policy: condition {condition_name!r} is unclassified; run setup-pipeline set-condition {condition_name} true|false"
            )
        elif not condition_matches(transition_condition, conditions):
            failures.append(f"policy: phase {phase} is unnecessary because condition {condition_name!r} is false")

    route = routing.get("phases", {}).get(phase, {})
    required_profile = route.get("profile", "")
    requires_binding = bool(required_profile or route.get("roles"))
    configured_binding_path = ledger.get("model_bindings_file", "model-bindings.json")
    binding_path = project / configured_binding_path if isinstance(configured_binding_path, str) else project / "model-bindings.json"
    bindings: dict[str, Any] = {}
    conformance_policy: dict[str, Any] = {"mode": "advisory"}
    if not binding_path.is_file() and requires_binding:
        failures.append(f"model: binding file missing at {binding_path}")
    elif binding_path.is_file():
        validator = load_schema_validator(root)
        binding_schema = root / "templates" / "project" / "model-bindings.schema.json"
        failures.extend(
            f"schema: {configured_binding_path}: {error}"
            for error in validator.validate_file(binding_path, binding_schema)
        )
        try:
            binding_document = json.loads(binding_path.read_text(encoding="utf-8"))
            if binding_document.get("version") != "1":
                failures.append("model: binding file version must be '1'")
            bindings = binding_document.get("bindings", {})
            conformance_policy = binding_document.get("conformance_policy", {"mode": "advisory"})
            if not isinstance(bindings, dict):
                failures.append("model: bindings must be an object")
                bindings = {}
            unknown_profiles = sorted(set(bindings) - set(routing.get("profiles", {})))
            if unknown_profiles:
                failures.append(f"model: unknown capability profiles: {', '.join(unknown_profiles)}")
        except (json.JSONDecodeError, AttributeError) as error:
            failures.append(f"model: cannot read bindings at {binding_path}: {error}")

    for profile, binding in bindings.items():
        if isinstance(binding, dict):
            failures.extend(
                model_conformance_errors(root, project, machine, profile, binding, conformance_policy)
            )

    resolved: dict[str, str] = {}
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

    completion_contract = transition.get("completion", {}) if completion else {}
    if completion and not completion_contract:
        failures.append(f"completion: phase {phase} has no completion contract")
    requirements = completion_contract.get("requires", []) if completion else transition.get("requires", [])
    records = ledger.get("artifacts", {})
    loaded_json: dict[str, Any] = {}
    for requirement in requirements:
        if not applicable(requirement, tier, conditions):
            continue
        pattern = requirement["artifact"]
        matches = sorted(
            artifact for artifact in project.glob(pattern) if artifact.is_file()
        ) if any(character in pattern for character in "*?[") else [project / pattern]
        if not matches or not all(artifact.exists() for artifact in matches):
            if requirement.get("when_present"):
                continue
            failures.append(f"input: required artifact {pattern!r} missing")
            continue
        for artifact in matches:
            name = artifact.relative_to(project).as_posix()
            record = records.get(name, {}) if isinstance(records.get(name, {}), dict) else {}
            failures.extend(artifact_schema_errors(root, artifact, name, machine))
            if artifact.stat().st_size == 0:
                failures.append(f"input: required artifact {name!r} is empty")
            if name == "code-review.md":
                review_text = artifact.read_text(encoding="utf-8", errors="replace")
                assessment = re.search(r"\*\*Overall assessment\*\*:\s*(APPROVE|REQUEST_CHANGES|COMMENT)\b", review_text)
                if not assessment:
                    failures.append("semantic: code-review.md must contain '**Overall assessment**: APPROVE|REQUEST_CHANGES|COMMENT'")
                elif assessment.group(1) != "APPROVE":
                    failures.append(f"semantic: code-review.md must be APPROVE before acceptance, got {assessment.group(1)}")
            if record.get("status") == "invalidated" or record.get("invalidated_by"):
                failures.append(f"input: {name!r} is invalidated by {record.get('invalidated_by', 'ledger status')}")
            if record.get("status") == "draft":
                failures.append(f"input: {name!r} is still draft; attest it as ready, approved, or complete")
            if requirement.get("attested"):
                expected = record.get("sha256")
                if not expected:
                    failures.append(f"input: {name!r} has no sha256 attestation in the ledger")
                else:
                    actual = sha256(artifact)
                    if actual != expected:
                        failures.append(f"input: {name!r} changed since attested (ledger {expected[:12]}…, actual {actual[:12]}…)")
                resolved_contract = artifact_contract(machine, name)
                schema_name = resolved_contract[1].get("schema") if resolved_contract else None
                if schema_name:
                    schema_path = root / schema_name
                    recorded_schema = record.get("schema")
                    recorded_schema_hash = record.get("schema_sha256")
                    if recorded_schema and recorded_schema != schema_name:
                        failures.append(
                            f"schema: {name!r} was attested against {recorded_schema!r}, expected {schema_name!r}"
                        )
                    elif recorded_schema_hash and recorded_schema_hash != sha256(schema_path):
                        failures.append(
                            f"schema: {name!r} schema changed since attestation; revalidate and re-attest"
                        )
                    elif not recorded_schema_hash:
                        warnings.append(
                            f"{name!r} attestation predates schema provenance; current bytes were validated but should be re-attested"
                        )
            if "sha256_of" in requirement:
                source = project / requirement["sha256_of"]
                marker = artifact.read_text(encoding="utf-8", errors="replace").strip()
                if not source.is_file() or marker != sha256(source):
                    failures.append(
                        f"semantic: {name!r} must contain the sha256 of {requirement['sha256_of']!r}"
                    )
            if "json_pointer" in requirement:
                try:
                    document = json.loads(artifact.read_text(encoding="utf-8"))
                    loaded_json[name] = document
                    actual_value = pointer(document, requirement["json_pointer"])
                except (json.JSONDecodeError, KeyError, IndexError, ValueError) as error:
                    failures.append(f"semantic: cannot read {name}{requirement['json_pointer']}: {error}")
                    continue
                if "equals" in requirement and actual_value != requirement["equals"]:
                    failures.append(f"semantic: {name}{requirement['json_pointer']} must equal {requirement['equals']!r}, got {actual_value!r}")
                if "in" in requirement and actual_value not in requirement["in"]:
                    failures.append(f"semantic: {name}{requirement['json_pointer']} must be one of {requirement['in']!r}, got {actual_value!r}")

    for name, document in loaded_json.items():
        failures.extend(artifact_semantic_errors(name, document, tier))

    if phase in SPEC_GAP_GATE_PHASES:
        evidence = project / "evidence-handoff.json"
        if evidence.is_file():
            try:
                document = loaded_json.get("evidence-handoff.json") or json.loads(evidence.read_text(encoding="utf-8"))
                failures.extend(specification_gap_errors(document))
            except json.JSONDecodeError as error:
                failures.append(f"specification_gap: cannot read evidence-handoff.json: {error}")

    if phase == "4c" and behavior_pack_required(tier, conditions):
        failures.extend(behavior_pack_errors(root, project))

    human_gate = completion_contract.get("human_gate") if completion else transition.get("human_gate")
    if human_gate:
        signature = ledger.get("human_gates", {}).get(human_gate, {})
        authority_failures, assignments_configured = human_authority_errors(
            root, project, human_gate, tier, signature, machine, ledger
        )
        failures.extend(authority_failures)
        if not assignments_configured and not all(signature.get(key) for key in ("by", "at")):
            failures.append(f"human_gate: {human_gate!r} requires by and at")

    tier_route = machine["risk_policy"]["tiers"][tier]
    selected_phases = set(tier_route["required_phases"])
    selected_phases.update(
        conditional_phase
        for conditional_phase, rule in tier_route.get("conditional_phases", {}).items()
        if condition_matches(rule, conditions)
    )
    if phase not in selected_phases and phase not in {"-1"}:
        warnings.append(f"phase {phase} is outside the canonical {tier} route")
    return failures, warnings, {**transition, "tier": tier, "required_profile": required_profile, "resolved_models": resolved, "completion_check": completion}
# END_BLOCK_TRANSITION_EVALUATION


# START_BLOCK_CLI
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", help="pipeline phase, for example 4c or 6")
    parser.add_argument("project_dir", nargs="?", default=".")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--completion", action="store_true", help="check the phase completion contract instead of entry preconditions")
    args = parser.parse_args()
    failures, warnings, transition = evaluate(args.root.resolve(), Path(args.project_dir).resolve(), args.phase, args.completion)
    check_kind = "completion" if args.completion else "entry"
    print(f"=== preflight · phase {args.phase} · {check_kind} · {transition.get('skill', '?')} · {transition.get('tier', '?')} ===")
    for warning in warnings:
        print(f"WARN: {warning}")
    if failures:
        print("HALT — preconditions failed:")
        for failure in failures:
            print(f"  ✗ {failure}")
        return 1
    print("✓ policy ✓ models ✓ semantic inputs/attestations ✓ specification gaps ✓ human gate")
    print(f"required profile: {transition.get('required_profile', '')}; resolved models: {transition.get('resolved_models', {})}")
    print("agent must confirm its running runtime/model matches the resolved binding for its role")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
