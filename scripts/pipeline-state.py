#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Let a human initialize, attest, sign, and inspect the setup pipeline ledger safely.
# SCOPE: Project-local .pipeline-state.json mutations and downstream invalidation from pipeline-machine.json.
# DEPENDS: Python standard library, templates/project/.pipeline-state.json, and pipeline-machine.json.
# END_MODULE_CONTRACT
"""Human operator CLI for the setup pipeline ledger."""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


TIERS = ("T0", "T1", "T2", "T3", "T4")
ARTIFACT_STATUSES = ("draft", "ready", "approved", "complete")
RUNTIMES = ("claude", "codex", "opencode", "api", "manual", "self-hosted", "custom:<lowercase-slug>")
CONDITIONS = ("research_required", "frontend")


# START_BLOCK_LEDGER_IO
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    temporary = Path(raw)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def project_artifact(project: Path, name: str) -> tuple[Path, str]:
    artifact = (project / name).resolve()
    try:
        relative = artifact.relative_to(project).as_posix()
    except ValueError as error:
        raise ValueError("artifact must stay inside the project directory") from error
    if relative == ".pipeline-state.json":
        raise ValueError("the ledger cannot attest itself")
    return artifact, relative


def load_ledger(project: Path) -> tuple[Path, dict[str, Any]]:
    path = project / ".pipeline-state.json"
    if not path.is_file():
        raise ValueError(f"no ledger at {path}; run `setup-pipeline --project {project} init`")
    return path, read_json(path)


def selected_route(machine: dict[str, Any], ledger: dict[str, Any]) -> list[str]:
    tier = ledger.get("policy", {}).get("risk_tier")
    if tier is None:
        provisional = ["-1"]
        if ledger.get("policy", {}).get("conditions", {}).get("research_required") is True:
            provisional.append("0")
        return provisional
    route = machine.get("risk_policy", {}).get("tiers", {}).get(tier)
    if not isinstance(route, dict):
        return []
    selected = set(route.get("required_phases", []))
    conditions = ledger.get("policy", {}).get("conditions", {})
    for phase, rule in route.get("conditional_phases", {}).items():
        if conditions.get(rule.get("condition")) == rule.get("equals"):
            selected.add(phase)
    return [phase for phase in machine.get("transitions", {}) if phase in selected]


def next_selected_phase(machine: dict[str, Any], ledger: dict[str, Any]) -> str | None:
    route = selected_route(machine, ledger)
    current = ledger.get("phase")
    if current in route:
        index = route.index(current) + 1
        return route[index] if index < len(route) else None
    if current == "-1" and route:
        return route[0]
    return None


def load_preflight(root: Path) -> Any:
    spec = importlib.util.spec_from_file_location("setup_pipeline_preflight", root / "scripts" / "pipeline_preflight.py")
    if spec is None or spec.loader is None:
        raise ValueError("cannot load pipeline preflight evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def owner_for_artifact(machine: dict[str, Any], name: str) -> str | None:
    for pattern, ownership in machine.get("artifact_owners", {}).items():
        if fnmatch.fnmatch(name, pattern):
            return ownership.get("producer_phase")
    return None


def matching_policy_values(mapping: dict[str, Any], name: str) -> list[str]:
    """Return de-duplicated values from exact or glob policy keys matching an artifact path."""
    values: list[str] = []
    for pattern, configured in mapping.items():
        if fnmatch.fnmatch(name, pattern):
            for value in configured:
                if value not in values:
                    values.append(value)
    return values


def invalidate_after_policy_change(ledger: dict[str, Any], source: str) -> None:
    """Fail closed when a previously classified route decision changes."""
    preserved = {"product_brief.md", "evidence-handoff.json"}
    for name, record in ledger.setdefault("artifacts", {}).items():
        if name not in preserved and isinstance(record, dict) and record.get("sha256"):
            record["status"] = "invalidated"
            record["invalidated_by"] = source
    for gate in ledger.setdefault("human_gates", {}):
        ledger["human_gates"][gate] = {"by": None, "at": None}
# END_BLOCK_LEDGER_IO


# START_BLOCK_LEDGER_COMMANDS
def command_init(args: argparse.Namespace, root: Path, project: Path) -> int:
    target = project / ".pipeline-state.json"
    if target.exists() and not args.force:
        raise ValueError(f"{target} already exists; use --force only to replace it intentionally")
    project.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "templates" / "project" / ".pipeline-state.json", target)
    print(f"initialized {target}")
    return 0


def command_bootstrap(args: argparse.Namespace, root: Path, project: Path) -> int:
    """Copy missing project contracts without overwriting an adopted repository."""
    source = root / "templates" / "project"
    project.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    skipped: list[str] = []
    for item in sorted(source.rglob("*")):
        relative = item.relative_to(source)
        target = project / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if target.exists() or target.is_symlink():
            skipped.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, target)
        created.append(relative.as_posix())
    agents = project / "AGENTS.md"
    claude = project / "CLAUDE.md"
    if not agents.exists() and not agents.is_symlink() and claude.is_file():
        agents.symlink_to("CLAUDE.md")
        created.append("AGENTS.md -> CLAUDE.md")
    print(f"bootstrapped {project}: {len(created)} created, {len(skipped)} preserved")
    for name in created:
        print(f"  + {name}")
    if skipped:
        print("preserved existing files; bootstrap never overwrites them")
    return 0


def command_migrate(args: argparse.Namespace, root: Path, project: Path) -> int:
    """Upgrade a version-2 ledger shape without changing attestations or signatures."""
    path, ledger = load_ledger(project)
    if ledger.get("version") != "2":
        raise ValueError("automatic migration supports only ledger version '2'; preserve this file and migrate older semantics manually")
    original = json.dumps(ledger, sort_keys=True)
    changes: list[str] = []
    if ledger.get("phase") == "discovery":
        ledger["phase"] = "-1"
        changes.append("phase discovery -> -1")
    policy = ledger.setdefault("policy", {})
    conditions = policy.setdefault("conditions", {})
    for name in CONDITIONS:
        if name not in conditions:
            conditions[name] = None
            changes.append(f"added unclassified condition {name}")
    for legacy in ("skipped_gates", "skip_contract"):
        if legacy in policy:
            del policy[legacy]
            changes.append(f"archived obsolete policy.{legacy}")
    gates = ledger.setdefault("human_gates", {})
    if "phase_processes" not in ledger:
        ledger["phase_processes"] = {}
        changes.append("added phase_processes registry")
    if "stakeholder_input_confirmed" in gates:
        del gates["stakeholder_input_confirmed"]
        changes.append("archived obsolete stakeholder_input_confirmed gate")
    for name in ("viz_before_tickets", "contract_locked", "human_acceptance"):
        if name not in gates:
            gates[name] = {"by": None, "at": None}
            changes.append(f"added gate {name}")
    for name, record in ledger.setdefault("artifacts", {}).items():
        if isinstance(record, dict):
            if "status" not in record:
                record["status"] = "ready" if record.get("sha256") else "draft"
                changes.append(f"added status for {name}")
            if "invalidated_by" not in record:
                record["invalidated_by"] = None
                changes.append(f"added invalidated_by for {name}")
    if json.dumps(ledger, sort_keys=True) == original:
        print("ledger already current; no migration needed")
        return 0
    backup = path.with_name(f"{path.name}.bak-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    shutil.copyfile(path, backup)
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"migrated {path}; recoverable backup: {backup}")
    for change in changes:
        print(f"  + {change}")
    return 0


def command_set_tier(args: argparse.Namespace, root: Path, project: Path) -> int:
    if not args.reason.strip():
        raise ValueError("--reason must be non-empty accountable text")
    path, ledger = load_ledger(project)
    policy = ledger.setdefault("policy", {})
    previous = policy.get("risk_tier")
    if previous is not None and previous != args.tier:
        invalidate_after_policy_change(ledger, "policy.risk_tier")
        ledger["phase"] = "-1"
        print(f"invalidated downstream evidence and human gates: risk tier changed from {previous} to {args.tier}")
        print("reset current phase to -1; re-enter the newly selected route atomically")
    policy["risk_tier"] = args.tier
    policy["tier_reason"] = args.reason
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"risk tier: {args.tier} — {args.reason}")
    return 0


def command_set_condition(args: argparse.Namespace, root: Path, project: Path) -> int:
    path, ledger = load_ledger(project)
    conditions = ledger.setdefault("policy", {}).setdefault("conditions", {})
    selected = args.value == "true"
    previous = conditions.get(args.condition)
    if previous is not None and previous != selected:
        invalidate_after_policy_change(ledger, f"policy.conditions.{args.condition}")
        ledger["phase"] = "-1"
        print(f"invalidated downstream evidence and human gates: condition {args.condition} changed")
        print("reset current phase to -1; re-enter the newly selected route atomically")
    conditions[args.condition] = selected
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"condition {args.condition}: {args.value}")
    return 0


def command_set_process(args: argparse.Namespace, root: Path, project: Path) -> int:
    """Bind a trusted skill-owned validator to any machine phase."""
    machine = read_json(root / "pipeline-machine.json")
    if args.phase not in machine.get("transitions", {}):
        raise ValueError(f"unknown phase {args.phase!r}")
    preflight = load_preflight(root)
    preflight.load_phase_process_descriptor(root, args.skill)
    path, ledger = load_ledger(project)
    ledger.setdefault("phase_processes", {})[args.phase] = {"skill": args.skill}
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"phase process {args.phase}: {args.skill}")
    return 0


def command_attest(args: argparse.Namespace, root: Path, project: Path) -> int:
    path, ledger = load_ledger(project)
    machine = read_json(root / "pipeline-machine.json")
    records = ledger.setdefault("artifacts", {})
    changed_sources: list[str] = []
    refreshed: set[str] = set()
    for raw_name in args.artifacts:
        artifact, name = project_artifact(project, raw_name)
        owner = owner_for_artifact(machine, name)
        if owner is not None and ledger.get("phase") != owner:
            raise ValueError(
                f"artifact {name!r} belongs to phase {owner}; current phase is {ledger.get('phase')!r}. "
                f"Run `setup-pipeline enter {owner}` and the phase guard before producing or attesting it."
            )
        if not artifact.is_file():
            raise ValueError(f"artifact not found: {artifact}")
        current = sha256(artifact)
        prior = records.get(name, {}) if isinstance(records.get(name), dict) else {}
        previous_hash = prior.get("sha256")
        records[name] = {"sha256": current, "status": args.status, "invalidated_by": None}
        if not previous_hash or previous_hash != current:
            refreshed.add(name)
        if previous_hash and previous_hash != current:
            changed_sources.append(name)
        print(f"attested {name}: sha256:{current}")

    for source in changed_sources:
        for consumer in matching_policy_values(machine.get("invalidations", {}), source):
            record = records.get(consumer)
            if isinstance(record, dict) and record.get("sha256") and consumer not in refreshed:
                record["status"] = "invalidated"
                record["invalidated_by"] = source
                print(f"invalidated {consumer}: upstream {source} changed")
        for gate in matching_policy_values(machine.get("gate_invalidations", {}), source):
            signature = ledger.setdefault("human_gates", {}).get(gate)
            if isinstance(signature, dict) and (signature.get("by") or signature.get("at")):
                ledger["human_gates"][gate] = {"by": None, "at": None}
                print(f"invalidated human gate {gate}: upstream {source} changed")
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    return 0


def command_sign(args: argparse.Namespace, root: Path, project: Path) -> int:
    if not args.by.strip():
        raise ValueError("--by must be a non-empty person or account identity")
    path, ledger = load_ledger(project)
    machine = read_json(root / "pipeline-machine.json")
    owner = machine.get("gate_owners", {}).get(args.gate)
    if owner is not None and ledger.get("phase") != owner:
        raise ValueError(f"human gate {args.gate!r} is owned by phase {owner}; current phase is {ledger.get('phase')!r}")
    gates = ledger.setdefault("human_gates", {})
    if args.gate not in gates:
        known = ", ".join(sorted(gates)) or "none"
        raise ValueError(f"unknown human gate {args.gate!r}; known: {known}")
    gates[args.gate] = {"by": args.by, "at": timestamp()}
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"signed {args.gate} by {args.by}")
    return 0


def command_enter(args: argparse.Namespace, root: Path, project: Path) -> int:
    machine = read_json(root / "pipeline-machine.json")
    if args.phase not in machine.get("transitions", {}):
        known = ", ".join(machine.get("transitions", {}))
        raise ValueError(f"unknown phase {args.phase!r}; known: {known}")
    path, ledger = load_ledger(project)
    route = selected_route(machine, ledger)
    expected = next_selected_phase(machine, ledger)
    current = ledger.get("phase")
    if args.phase == current:
        raise ValueError(f"phase {args.phase!r} is already current; use `setup-pipeline guard {args.phase}`")
    is_rework = args.phase == "-1" or (
        args.phase in route and current in route and route.index(args.phase) < route.index(current)
    )
    if expected is None and not is_rework:
        if ledger.get("policy", {}).get("risk_tier") is None:
            raise ValueError("route classification is incomplete; finish discovery and set the evidence-based risk tier first")
        raise ValueError(f"no next phase is available from current phase {ledger.get('phase')!r}")
    if args.phase != expected and not is_rework:
        raise ValueError(f"next applicable phase is {expected!r}, not {args.phase!r}; forward jumps are forbidden")

    candidate = copy.deepcopy(ledger)
    candidate["phase"] = args.phase
    preflight = load_preflight(root)
    _, current_process_failures, current_process_next = preflight.phase_process_check(root, project, current, ledger)
    if current_process_failures and not is_rework:
        rendered = "\n  - ".join(current_process_failures)
        raise ValueError(
            f"cannot leave phase {current}; its process validator is blocked:\n  - {rendered}\n"
            f"next action: {current_process_next}"
        )
    failures, warnings, _ = preflight.evaluate(root, project, args.phase, ledger_override=candidate)
    if failures:
        rendered = "\n  - ".join(failures)
        raise ValueError(f"cannot enter phase {args.phase}; ledger unchanged:\n  - {rendered}")
    for warning in warnings:
        print(f"WARN: {warning}")
    candidate["updated_at"] = timestamp()
    write_json(path, candidate)
    print(f"entered phase {args.phase} atomically{' for rework' if is_rework else ''}")
    print(f"guard before the first phase-owned write: setup-pipeline --project {project} guard {args.phase}")
    return 0


def command_set_phase(args: argparse.Namespace, root: Path, project: Path) -> int:
    """Backward-compatible name with atomic entry semantics."""
    print("DEPRECATED: set-phase is an atomic alias; use `setup-pipeline enter`", file=sys.stderr)
    return command_enter(args, root, project)


def command_guard(args: argparse.Namespace, root: Path, project: Path) -> int:
    _, ledger = load_ledger(project)
    if ledger.get("phase") != args.phase:
        raise ValueError(f"phase guard denied: ledger is {ledger.get('phase')!r}, requested {args.phase!r}")
    preflight = load_preflight(root)
    failures, warnings, _ = preflight.evaluate(root, project, args.phase)
    if failures:
        rendered = "\n  - ".join(failures)
        raise ValueError(f"phase guard denied for {args.phase}:\n  - {rendered}")
    for warning in warnings:
        print(f"WARN: {warning}")
    print(f"phase guard PASS: {args.phase}")
    return 0


def required_route_profiles(root: Path, route: list[str]) -> set[str]:
    routing = read_json(root / "model-routing.json")
    profiles: set[str] = set()
    for phase in route:
        phase_route = routing.get("phases", {}).get(phase, {})
        if phase_route.get("profile"):
            profiles.add(phase_route["profile"])
        profiles.update(phase_route.get("roles", {}).values())
    return profiles


def model_routing_readiness(root: Path, project: Path, route: list[str]) -> tuple[str, list[str], list[str]]:
    required = required_route_profiles(root, route)
    if not required:
        return "READY", [], []
    binding_path = project / "model-bindings.json"
    if not binding_path.is_file():
        return "UNCONFIGURED", sorted(required), []
    try:
        document = read_json(binding_path)
    except ValueError as error:
        return "PARTIALLY_CONFIGURED", sorted(required), [str(error)]
    bindings = document.get("bindings", {})
    preflight = load_preflight(root)
    ready = {
        profile
        for profile in required
        if preflight.resolve_binding(bindings, profile) is not None
    }
    missing = sorted(required - ready)
    issues: list[str] = []
    routing = read_json(root / "model-routing.json")
    for phase in route:
        phase_route = routing.get("phases", {}).get(phase, {})
        for group in phase_route.get("distinct_roles", []):
            model_ids = []
            for role in group:
                profile = phase_route.get("roles", {}).get(role)
                binding = preflight.resolve_binding(bindings, profile) if profile else None
                if binding is not None:
                    model_ids.append(binding[1])
            if len(model_ids) == len(group) and len(set(model_ids)) != len(model_ids):
                issues.append(f"phase {phase} roles {group} must use distinct model IDs")
    if not ready:
        return "UNCONFIGURED", missing, issues
    return ("READY", [], []) if not missing and not issues else ("PARTIALLY_CONFIGURED", missing, issues)


def blocking_human_request_id(failures: list[str]) -> str | None:
    """Resolve a named gate failure to its HumanRequest catalog ID."""
    prefix = "human_gate: '"
    for failure in failures:
        if failure.startswith(prefix):
            return failure[len(prefix):].split("'", 1)[0]
    return None


def model_binding_request_context(missing_profiles: list[str], routing_issues: list[str]) -> list[str]:
    context = list(routing_issues)
    if missing_profiles:
        context.insert(0, "missing profiles: " + ", ".join(missing_profiles))
    return context


def render_human_request(
    root: Path,
    project: Path,
    request_id: str,
    request: dict[str, Any],
    *,
    context: list[str] | None = None,
) -> None:
    """Render one self-contained human pause with resolvable local references."""
    print(f"human request: {request_id}")
    print(f"authority: {request['authority']}")
    print(f"question: {request['question']}")
    print(f"why needed: {request['why_needed']}")
    if context:
        print("current context:")
        for item in context:
            print(f"  - {item}")
    print("evidence files:")
    for relative in request.get("evidence_refs", []):
        path = project / relative
        print(f"  - {path} [{'exists' if path.exists() else 'missing'}]")
    if request.get("setup_refs"):
        print("instructions:")
        for relative in request["setup_refs"]:
            path = root / relative
            print(f"  - {path} [{'exists' if path.exists() else 'missing'}]")
    response = request["response"]
    print(f"response format: {response['mode']}")
    if response["mode"] == "file":
        print(f"  file: {project / response['path']}")
        print(f"  schema: {project / response['schema']}")
    else:
        print("  " + json.dumps(response["format"], ensure_ascii=False, sort_keys=True))
        if response.get("record_command"):
            print(f"  record accepted response: {response['record_command']}")
    print("allowed responses: " + ", ".join(request["allowed_responses"]))
    print("consequences:")
    for outcome, consequence in request["consequences"].items():
        print(f"  {outcome}: {consequence}")
    print(f"resume: {request['resume_action']}")


def command_status(args: argparse.Namespace, root: Path, project: Path) -> int:
    _, ledger = load_ledger(project)
    machine = read_json(root / "pipeline-machine.json")
    policy = ledger.get("policy", {})
    phase = ledger.get("phase", "<unset>")
    transition = machine.get("transitions", {}).get(phase, {})
    print(f"project: {project}")
    print(f"current stage: {phase} — {transition.get('skill', 'unknown process')}")
    print(f"phase: {phase}")
    print(f"risk tier: {policy.get('risk_tier', '<unset>')}")
    print(f"tier reason: {policy.get('tier_reason', '<unset>')}")
    print("conditions:")
    conditions = policy.get("conditions", {})
    for name in CONDITIONS:
        value = conditions.get(name)
        print(f"  {name}: {'unclassified' if value is None else str(value).lower()}")
    print("artifacts:")
    for name, record in sorted(ledger.get("artifacts", {}).items()):
        if isinstance(record, dict):
            digest = record.get("sha256")
            digest_view = f"{digest[:12]}…" if isinstance(digest, str) and digest else "unattested"
            print(f"  {name}: {record.get('status', '<unset>')} · {digest_view} · invalidated_by={record.get('invalidated_by')}")
    print("human gates:")
    for name, signature in sorted(ledger.get("human_gates", {}).items()):
        signature = signature if isinstance(signature, dict) else {}
        print(f"  {name}: {signature.get('by') or 'unsigned'} · {signature.get('at') or '—'}")
    preflight = load_preflight(root)
    process_skill, process_failures, process_next = preflight.phase_process_check(root, project, phase, ledger)
    print(f"phase process: {process_skill or transition.get('skill', 'unknown process')}")
    if process_failures:
        if policy.get("risk_tier") is None:
            provisional = next_selected_phase(machine, ledger)
            if provisional == "0":
                routing_readiness, missing_profiles, routing_issues = model_routing_readiness(root, project, ["0"])
                print(f"model routing: {routing_readiness} (provisional research only)")
                if missing_profiles:
                    print("missing required profiles: " + ", ".join(missing_profiles))
                for issue in routing_issues:
                    print(f"model routing issue: {issue}")
            else:
                print("model routing: DEFERRED — route not classified")
        else:
            route_policy = machine["risk_policy"]["tiers"][policy["risk_tier"]]
            routed = set(route_policy["required_phases"])
            for routed_phase, rule in route_policy.get("conditional_phases", {}).items():
                if conditions.get(rule["condition"]) == rule["equals"]:
                    routed.add(routed_phase)
            ordered_route = [item for item in machine["transitions"] if item in routed]
            routing_readiness, missing_profiles, routing_issues = model_routing_readiness(root, project, ordered_route)
            print(f"model routing: {routing_readiness}")
            if missing_profiles:
                print("missing required profiles: " + ", ".join(missing_profiles))
            for issue in routing_issues:
                print(f"model routing issue: {issue}")
        print("readiness: BLOCKED")
        print("transition: continue_now")
        print("phase-process blockers:")
        for failure in process_failures:
            print(f"  - {failure}")
        print(f"next action: {process_next}")
        print(f"current check: setup-preflight {phase} {project}")
        return 0
    if policy.get("risk_tier") is None:
        provisional_next = next_selected_phase(machine, ledger)
        if phase == "0":
            record = ledger.get("artifacts", {}).get("docs/research-state.json", {})
            ready = isinstance(record, dict) and bool(record.get("sha256")) and record.get("status") != "draft"
            print("model routing: DEFERRED — final route not classified")
            print(f"readiness: {'READY' if ready else 'BLOCKED'}")
            print("transition: continue_now")
            if ready:
                print("next phase: -1")
                print(f"next action: setup-pipeline --project {project} enter -1, then classify the evidence-based route")
            else:
                print("next action: complete and attest docs/research-state.json before returning to discovery")
        elif provisional_next == "0":
            readiness, missing_profiles, routing_issues = model_routing_readiness(root, project, ["0"])
            print(f"model routing: {readiness} (provisional research only)")
            if missing_profiles:
                print("missing required profiles: " + ", ".join(missing_profiles))
            for issue in routing_issues:
                print(f"model routing issue: {issue}")
            if missing_profiles or routing_issues:
                print("readiness: BLOCKED")
                print("transition: waiting_for_human")
                print("next action: configure the Phase 0 model profiles, then rerun setup-pipeline status")
                render_human_request(
                    root,
                    project,
                    "model_bindings",
                    machine["human_requests"]["model_bindings"],
                    context=model_binding_request_context(missing_profiles, routing_issues),
                )
            else:
                candidate = copy.deepcopy(ledger)
                candidate["phase"] = "0"
                preflight = load_preflight(root)
                failures, _, _ = preflight.evaluate(root, project, "0", ledger_override=candidate)
                print(f"readiness: {'BLOCKED' if failures else 'READY'}")
                print("transition: continue_now")
                if failures:
                    print("next-phase blockers:")
                    for failure in failures:
                        print(f"  - {failure}")
                    print("next action: resolve the listed blockers, then rerun setup-pipeline status")
                else:
                    print(f"next action: setup-pipeline --project {project} enter 0")
        else:
            print("model routing: DEFERRED — route not classified")
            preflight = load_preflight(root)
            failures, _, _ = preflight.evaluate(root, project, ledger.get("phase"))
            if failures:
                print("readiness: BLOCKED")
                print("transition: continue_now")
                print("current-phase blockers:")
                for failure in failures:
                    print(f"  - {failure}")
                print("next action: resolve the listed current-phase blockers, then continue discovery")
            else:
                print("readiness: READY")
                print("transition: continue_now")
                print("next action: complete discovery artifacts, then select the evidence-based risk tier")
        print(f"current check: setup-preflight {phase} {project}")
    else:
        tier = policy["risk_tier"]
        route = machine["risk_policy"]["tiers"][tier]
        selected = set(route["required_phases"])
        unresolved: list[str] = []
        for phase, rule in route.get("conditional_phases", {}).items():
            value = conditions.get(rule["condition"])
            if value is None:
                unresolved.append(rule["condition"])
            elif value == rule["equals"]:
                selected.add(phase)
        ordered = [phase for phase in machine["transitions"] if phase in selected]
        print(f"route: {' -> '.join(ordered)}")
        if unresolved:
            print("route incomplete: classify conditions with setup-pipeline set-condition: " + ", ".join(sorted(set(unresolved))))
        next_phase = next_selected_phase(machine, ledger)
        readiness, missing_profiles, routing_issues = model_routing_readiness(root, project, ordered)
        print(f"model routing: {readiness}")
        if missing_profiles:
            print("missing required profiles: " + ", ".join(missing_profiles))
        for issue in routing_issues:
            print(f"model routing issue: {issue}")
        if next_phase is None:
            preflight = load_preflight(root)
            failures, _, _ = preflight.evaluate(root, project, ledger.get("phase"), completion=True)
            print("next phase: none")
            if failures:
                request_id = blocking_human_request_id(failures)
                print(f"transition: {'waiting_for_human' if request_id else 'continue_now'}")
                print("completion blockers:")
                for failure in failures:
                    print(f"  - {failure}")
                print("next action: complete the listed review evidence or human acceptance, then rerun setup-pipeline status")
                if request_id:
                    render_human_request(
                        root, project, request_id, machine["human_requests"][request_id], context=failures
                    )
            else:
                print("transition: complete")
        else:
            print(f"next phase: {next_phase}")
            if missing_profiles or routing_issues:
                print("transition: waiting_for_human")
                print("next action: configure required model profiles in model-bindings.json, then rerun setup-pipeline status")
                render_human_request(
                    root,
                    project,
                    "model_bindings",
                    machine["human_requests"]["model_bindings"],
                    context=model_binding_request_context(missing_profiles, routing_issues),
                )
            else:
                candidate = copy.deepcopy(ledger)
                candidate["phase"] = next_phase
                preflight = load_preflight(root)
                failures, _, _ = preflight.evaluate(root, project, next_phase, ledger_override=candidate)
                request_id = blocking_human_request_id(failures)
                print(f"transition: {'waiting_for_human' if request_id else 'continue_now'}")
                if failures:
                    print("next-phase blockers:")
                    for failure in failures:
                        print(f"  - {failure}")
                    print("next action: resolve the listed blockers, then rerun setup-pipeline status")
                    if request_id:
                        render_human_request(
                            root, project, request_id, machine["human_requests"][request_id], context=failures
                        )
                else:
                    print(f"next action: setup-pipeline --project {project} enter {next_phase}")
    return 0


def command_values(args: argparse.Namespace, root: Path, project: Path) -> int:
    machine = read_json(root / "pipeline-machine.json")
    routing = read_json(root / "model-routing.json")
    evidence_schema = read_json(root / "templates" / "project" / "evidence-handoff.schema.json")
    evidence = evidence_schema["properties"]
    gaps = evidence["spec_gaps"]["items"]["properties"]
    experiment = evidence["cheapest_next_experiment"]["properties"]
    gates = {
        gate
        for transition in machine["transitions"].values()
        for gate in (transition.get("human_gate"), transition.get("completion", {}).get("human_gate"))
        if gate
    }
    print("phases: " + ", ".join(machine["transitions"]))
    print("risk tiers:")
    for tier, data in machine["risk_policy"]["tiers"].items():
        conditional = data.get("conditional_phases", {})
        print(f"  {tier}: {data['criteria']}")
        print(f"    required: {', '.join(data['required_phases'])}")
        if conditional:
            print(
                "    conditional: "
                + "; ".join(
                    f"{phase} when {rule['condition']}={str(rule['equals']).lower()} ({rule['description']})"
                    for phase, rule in conditional.items()
                )
            )
    print("human gates: " + ", ".join(sorted(gates)))
    print("human request contracts:")
    for request_id, request in machine["human_requests"].items():
        print(f"  {request_id}: authority={request['authority']}, response={request['response']['mode']}")
    print("route conditions: research_required=true|false, frontend=true|false")
    print("artifact statuses: " + ", ".join(ARTIFACT_STATUSES) + " (invalidated is machine-set)")
    print("capability profiles: " + ", ".join(routing["profiles"]))
    print("runtimes: " + ", ".join(RUNTIMES))
    print("evidence-handoff values:")
    print("  validation_stage: " + ", ".join(evidence["validation_stage"]["enum"]))
    print("  decision: " + ", ".join(evidence["decision"]["enum"]))
    for name in ("kind", "impact", "materiality", "disposition", "status"):
        print(f"  spec_gaps[].{name}: " + ", ".join(gaps[name]["enum"]))
    print("  cheapest_next_experiment.type: " + ", ".join(experiment["type"]["enum"]))
    print("schema owners:")
    for name in (
        "evidence-handoff.schema.json",
        "model-bindings.schema.json",
        "pipeline-state.schema.json",
        "risk-review.schema.json",
        "issues-manifest.schema.json",
        "scaffold-manifest.schema.json",
        "build-evidence.schema.json",
        "rollout-plan.schema.json",
    ):
        print(f"  {name}: {root / 'templates' / 'project' / name}")
    return 0
# END_BLOCK_LEDGER_COMMANDS


# START_BLOCK_CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="project directory (default: current directory)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap", help="copy every missing project template without overwriting existing files")
    bootstrap.set_defaults(handler=command_bootstrap)

    migrate = subparsers.add_parser("migrate", help="upgrade an existing version-2 ledger with a recoverable backup")
    migrate.set_defaults(handler=command_migrate)

    init = subparsers.add_parser("init", help="copy only the canonical ledger template into the project")
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=command_init)

    tier = subparsers.add_parser("set-tier", help="record the selected risk tier and rationale")
    tier.add_argument("tier", choices=TIERS)
    tier.add_argument("--reason", required=True)
    tier.set_defaults(handler=command_set_tier)

    condition = subparsers.add_parser("set-condition", help="record a boolean conditional-route decision")
    condition.add_argument("condition", choices=CONDITIONS)
    condition.add_argument("value", choices=("true", "false"))
    condition.set_defaults(handler=command_set_condition)

    process = subparsers.add_parser("set-process", help="bind a trusted skill validator to a machine phase")
    process.add_argument("phase")
    process.add_argument("skill")
    process.set_defaults(handler=command_set_process)

    attest = subparsers.add_parser("attest", help="register current artifact hashes and invalidate stale consumers")
    attest.add_argument("artifacts", nargs="+")
    attest.add_argument("--status", default="ready", choices=ARTIFACT_STATUSES)
    attest.set_defaults(handler=command_attest)

    sign = subparsers.add_parser("sign", help="record a named human gate signature")
    sign.add_argument("gate")
    sign.add_argument("--by", required=True)
    sign.set_defaults(handler=command_sign)

    enter = subparsers.add_parser("enter", help="atomically validate and enter the next applicable phase")
    enter.add_argument("phase")
    enter.set_defaults(handler=command_enter)

    guard = subparsers.add_parser("guard", help="fail closed unless the current phase and its entry preflight are valid")
    guard.add_argument("phase")
    guard.set_defaults(handler=command_guard)

    phase = subparsers.add_parser("set-phase", help="deprecated atomic alias for enter")
    phase.add_argument("phase")
    phase.set_defaults(handler=command_set_phase)

    status = subparsers.add_parser("status", help="show current ledger state and the next preflight command")
    status.set_defaults(handler=command_status)

    values = subparsers.add_parser("values", help="show allowed phases, tiers, gates, statuses, profiles, runtimes, and schema owners")
    values.set_defaults(handler=command_values)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(__file__).resolve().parents[1]
    project = args.project.expanduser().resolve()
    try:
        return args.handler(args, root, project)
    except ValueError as error:
        print(f"setup-pipeline: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
