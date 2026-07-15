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


def command_init(args: argparse.Namespace, root: Path, project: Path) -> int:
    target = project / ".pipeline-state.json"
    if target.exists() and not args.force:
        raise ValueError(f"{target} already exists; use --force only to replace it intentionally")
    project.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "templates" / "project" / ".pipeline-state.json", target)
    print(f"initialized {target}")
    return 0


def command_set_tier(args: argparse.Namespace, root: Path, project: Path) -> int:
    path, ledger = load_ledger(project)
    policy = ledger.setdefault("policy", {})
    policy["risk_tier"] = args.tier
    policy["tier_reason"] = args.reason
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    print(f"risk tier: {args.tier} — {args.reason}")
    return 0


def command_attest(args: argparse.Namespace, root: Path, project: Path) -> int:
    path, ledger = load_ledger(project)
    machine = read_json(root / "pipeline-machine.json")
    records = ledger.setdefault("artifacts", {})
    changed_sources: list[str] = []
    for raw_name in args.artifacts:
        artifact, name = project_artifact(project, raw_name)
        if not artifact.is_file():
            raise ValueError(f"artifact not found: {artifact}")
        current = sha256(artifact)
        prior = records.get(name, {}) if isinstance(records.get(name), dict) else {}
        previous_hash = prior.get("sha256")
        records[name] = {"sha256": current, "status": args.status, "invalidated_by": None}
        if previous_hash and previous_hash != current:
            changed_sources.append(name)
        print(f"attested {name}: sha256:{current}")

    for source in changed_sources:
        for consumer in machine.get("invalidations", {}).get(source, []):
            record = records.get(consumer)
            if isinstance(record, dict) and record.get("sha256"):
                record["status"] = "invalidated"
                record["invalidated_by"] = source
                print(f"invalidated {consumer}: upstream {source} changed")
    ledger["updated_at"] = timestamp()
    write_json(path, ledger)
    return 0


def command_sign(args: argparse.Namespace, root: Path, project: Path) -> int:
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
    print(f"next check: bash ~/.claude/scripts/pipeline-preflight.sh {ledger.get('phase', '<phase>')} {project}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="project directory (default: current directory)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="copy the canonical ledger template into the project")
    init.add_argument("--force", action="store_true")
    init.set_defaults(handler=command_init)

    tier = subparsers.add_parser("set-tier", help="record the selected risk tier and rationale")
    tier.add_argument("tier", choices=TIERS)
    tier.add_argument("--reason", required=True)
    tier.set_defaults(handler=command_set_tier)

    attest = subparsers.add_parser("attest", help="register current artifact hashes and invalidate stale consumers")
    attest.add_argument("artifacts", nargs="+")
    attest.add_argument("--status", default="ready", choices=("draft", "ready", "approved", "complete"))
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
