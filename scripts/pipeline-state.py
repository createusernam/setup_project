#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Let a human initialize, attest, sign, and inspect the setup pipeline ledger safely.
# SCOPE: Project-local .pipeline-state.json mutations and downstream invalidation from pipeline-machine.json.
# DEPENDS: Python standard library, templates/project/.pipeline-state.json, and pipeline-machine.json.
# END_MODULE_CONTRACT
"""Human operator CLI for the setup pipeline ledger."""

from __future__ import annotations

import argparse
import hashlib
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
        print(f"invalidated downstream evidence and human gates: risk tier changed from {previous} to {args.tier}")
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
        print(f"invalidated downstream evidence and human gates: condition {args.condition} changed")
    conditions[args.condition] = selected
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"condition {args.condition}: {args.value}")
    return 0


def command_attest(args: argparse.Namespace, root: Path, project: Path) -> int:
    path, ledger = load_ledger(project)
    machine = read_json(root / "pipeline-machine.json")
    records = ledger.setdefault("artifacts", {})
    changed_sources: list[str] = []
    refreshed: set[str] = set()
    for raw_name in args.artifacts:
        artifact, name = project_artifact(project, raw_name)
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
        for consumer in machine.get("invalidations", {}).get(source, []):
            record = records.get(consumer)
            if isinstance(record, dict) and record.get("sha256") and consumer not in refreshed:
                record["status"] = "invalidated"
                record["invalidated_by"] = source
                print(f"invalidated {consumer}: upstream {source} changed")
        for gate in machine.get("gate_invalidations", {}).get(source, []):
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
    gates = ledger.setdefault("human_gates", {})
    if args.gate not in gates:
        known = ", ".join(sorted(gates)) or "none"
        raise ValueError(f"unknown human gate {args.gate!r}; known: {known}")
    gates[args.gate] = {"by": args.by, "at": timestamp()}
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"signed {args.gate} by {args.by}")
    return 0


def command_set_phase(args: argparse.Namespace, root: Path, project: Path) -> int:
    machine = read_json(root / "pipeline-machine.json")
    if args.phase not in machine.get("transitions", {}):
        known = ", ".join(machine.get("transitions", {}))
        raise ValueError(f"unknown phase {args.phase!r}; known: {known}")
    path, ledger = load_ledger(project)
    ledger["phase"] = args.phase
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"current phase: {args.phase}")
    return 0


def command_status(args: argparse.Namespace, root: Path, project: Path) -> int:
    _, ledger = load_ledger(project)
    policy = ledger.get("policy", {})
    print(f"project: {project}")
    print(f"phase: {ledger.get('phase', '<unset>')}")
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
    if policy.get("risk_tier") is None:
        print("next action: complete discovery artifacts, then select the evidence-based risk tier")
    else:
        machine = read_json(root / "pipeline-machine.json")
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
        print(f"next entry check: setup-preflight {ledger.get('phase', '<phase>')} {project}")
        if ledger.get("phase") == "7":
            print(f"after review + human signature: setup-preflight 7 {project} --completion")
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

    attest = subparsers.add_parser("attest", help="register current artifact hashes and invalidate stale consumers")
    attest.add_argument("artifacts", nargs="+")
    attest.add_argument("--status", default="ready", choices=ARTIFACT_STATUSES)
    attest.set_defaults(handler=command_attest)

    sign = subparsers.add_parser("sign", help="record a named human gate signature")
    sign.add_argument("gate")
    sign.add_argument("--by", required=True)
    sign.set_defaults(handler=command_sign)

    phase = subparsers.add_parser("set-phase", help="record the current machine phase")
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
