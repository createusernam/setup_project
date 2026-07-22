#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Own canonical JSON planning state and deterministically render human Markdown views.
# SCOPE: Initialize, render, and check task_plan/findings/progress state in one plan directory.
# DEPENDS: Python standard library.
# END_MODULE_CONTRACT
"""Single-writer planning state: JSON is canonical; Markdown is a generated view."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from typing import Any


class PlanningStateError(ValueError):
    """A user-fixable planning state or schema error."""


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        stream.write(value.rstrip() + "\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def schema_validator() -> Any:
    path = Path(__file__).resolve().parents[3] / "scripts" / "json_schema.py"
    spec = importlib.util.spec_from_file_location("setup_json_schema", path)
    if not spec or not spec.loader:
        raise PlanningStateError(f"cannot load schema validator at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_and_validate(directory: Path) -> dict[str, dict[str, Any]]:
    validator = schema_validator()
    documents: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for stem in ("task_plan", "findings", "progress"):
        document_path = directory / f"{stem}.json"
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / f"{stem.replace('_', '-')}.schema.json"
        try:
            document = json.loads(document_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"{document_path.name}: {error}")
            continue
        documents[stem] = document
        failures.extend(f"{document_path.name}: {error}" for error in validator.validate_file(document_path, schema_path))

    plan = documents.get("task_plan")
    if isinstance(plan, dict):
        phases = plan.get("phases", [])
        numbers = [phase.get("n") for phase in phases if isinstance(phase, dict)]
        if len(numbers) != len(set(numbers)):
            failures.append("task_plan.json: $.phases phase numbers must be unique")
        active = [phase for phase in phases if isinstance(phase, dict) and phase.get("status") == "in_progress"]
        current = plan.get("current_phase")
        if active and (len(active) != 1 or active[0].get("n") != current):
            failures.append("task_plan.json: $.current_phase must identify the single in_progress phase")
        if not active and phases and not all(phase.get("status") == "complete" for phase in phases if isinstance(phase, dict)):
            failures.append("task_plan.json: exactly one phase must be in_progress until all phases are complete")
        if current not in numbers:
            failures.append("task_plan.json: $.current_phase must identify an existing phase")
    if failures:
        raise PlanningStateError("planning state validation failed:\n  - " + "\n  - ".join(failures))
    return documents


def default_plan(created: str, template: str) -> dict[str, Any]:
    names = ["Data Discovery", "Analysis Plan", "Analysis", "Validation", "Delivery"] if template == "analytics" else [
        "Requirements & Discovery", "Planning & Structure", "Implementation", "Testing & Verification", "Delivery"
    ]
    return {
        "version": "2",
        "created": created,
        "goal": "[One sentence describing the end state]",
        "current_phase": 1,
        "phases": [
            {"n": index, "name": name, "status": "in_progress" if index == 1 else "pending", "tasks": [], "blockers": []}
            for index, name in enumerate(names, 1)
        ],
        "decisions": [],
        "errors": [],
    }


def render_plan(document: dict[str, Any]) -> str:
    lines = ["<!-- GENERATED FROM task_plan.json — DO NOT EDIT -->", "# Task Plan", "", "## Goal", str(document.get("goal", "")), "", "## Current Phase", f"Phase {document.get('current_phase', '')}", "", "## Phases", ""]
    for phase in document.get("phases", []):
        lines.append(f"### Phase {phase['n']}: {phase['name']}")
        for task in phase.get("tasks", []):
            checked = "x" if task.get("done") else " "
            lines.append(f"- [{checked}] {task.get('text', '')}")
        lines.append(f"- **Status:** {phase['status']}")
        for blocker in phase.get("blockers", []):
            lines.append(f"- **Blocker:** {blocker}")
        lines.append("")
    lines.extend(["## Decisions Made", "| Decision | Rationale |", "|---|---|"])
    lines.extend(f"| {item.get('decision', '')} | {item.get('rationale', '')} |" for item in document.get("decisions", []))
    lines.extend(["", "## Errors Encountered", "| Error | Resolution |", "|---|---|"])
    lines.extend(f"| {item.get('error', '')} | {item.get('resolution', '')} |" for item in document.get("errors", []))
    return "\n".join(lines)


def render_entries(title: str, entries: list[dict[str, Any]]) -> str:
    lines = [f"<!-- GENERATED FROM {title.lower().replace(' ', '_')}.json — DO NOT EDIT -->", f"# {title}", ""]
    if not entries:
        lines.append("- No entries yet.")
    for entry in entries:
        timestamp = entry.get("timestamp", "")
        topic = entry.get("topic") or entry.get("action") or "entry"
        finding = entry.get("finding") or entry.get("result") or ""
        lines.extend([f"## {timestamp} · {topic}", "", str(finding), ""])
        source = entry.get("source")
        if source:
            lines.extend([f"Source: `{source}`", ""])
        files = entry.get("files_touched")
        if files:
            lines.extend(["Files: " + ", ".join(f"`{item}`" for item in files), ""])
    return "\n".join(lines)


def render_all(directory: Path) -> None:
    documents = load_and_validate(directory)
    plan = documents["task_plan"]
    findings = documents["findings"]
    progress = documents["progress"]
    write_text(directory / "task_plan.md", render_plan(plan))
    write_text(directory / "findings.md", render_entries("Findings", findings.get("entries", [])))
    write_text(directory / "progress.md", render_entries("Progress", progress.get("entries", [])))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init")
    init.add_argument("directory", type=Path)
    init.add_argument("--template", choices=["default", "analytics"], default="default")
    init.add_argument("--created", default=datetime.now(timezone.utc).date().isoformat())
    render = subparsers.add_parser("render")
    render.add_argument("directory", type=Path)
    check = subparsers.add_parser("check")
    check.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.command == "init":
        directory.mkdir(parents=True, exist_ok=True)
        files = {
            "task_plan.json": default_plan(args.created, args.template),
            "findings.json": {"version": "2", "entries": []},
            "progress.json": {"version": "2", "entries": []},
        }
        for name, document in files.items():
            path = directory / name
            if not path.exists():
                write_json(path, document)
                print(f"Created {path}")
        render_all(directory)
        return 0
    if args.command == "render":
        render_all(directory)
        print(f"Rendered planning Markdown views in {directory}")
        return 0
    document = json.loads((directory / "task_plan.json").read_text(encoding="utf-8"))
    phases = document.get("phases", [])
    complete = sum(phase.get("status") == "complete" for phase in phases)
    print(json.dumps({"complete": complete, "total": len(phases), "all_complete": bool(phases) and complete == len(phases)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PlanningStateError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
