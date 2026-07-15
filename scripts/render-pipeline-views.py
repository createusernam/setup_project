#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Generate the canonical human phase table and Mermaid graph from pipeline-machine.json.
# SCOPE: Render docs/agent/PIPELINE-MACHINE.md or check that the committed snapshot is current.
# DEPENDS: Python standard library and pipeline-machine.json.
# END_MODULE_CONTRACT
"""Render or verify generated pipeline views."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render(machine: dict) -> str:
    transitions = machine["transitions"]
    lines = [
        "<!-- GENERATED FROM pipeline-machine.json — DO NOT EDIT -->",
        "# Executable pipeline map",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    phase_ids = {phase: "P" + phase.replace("-", "m").replace(".", "d") for phase in transitions}
    ordered = list(transitions)
    for phase, transition in transitions.items():
        lines.append(f'    {phase_ids[phase]}["{phase} · {transition["skill"]}"]')
    for left, right in zip(ordered, ordered[1:]):
        lines.append(f"    {phase_ids[left]} --> {phase_ids[right]}")
    lines.extend(["```", "", "| Phase | Skill | Tiers | Semantic inputs | Human gate |", "|---|---|---|---|---|"])
    for phase, transition in transitions.items():
        inputs = []
        for requirement in transition.get("requires", []):
            semantic = requirement.get("json_pointer", "")
            expected = requirement.get("equals", requirement.get("in", ""))
            inputs.append(f'`{requirement["artifact"]}{semantic}` {expected}'.strip())
        lines.append(f'| {phase} | `{transition["skill"]}` | {", ".join(transition["tiers"])} | {"<br>".join(inputs) or "—"} | `{transition.get("human_gate", "—")}` |')
    lines.extend(["", "Risk policy: " + " · ".join(f"{tier}={data['label']}" for tier, data in machine["risk_policy"]["tiers"].items())])
    conditions = []
    for tier, data in machine["risk_policy"]["tiers"].items():
        for phase, condition in data.get("conditional_phases", {}).items():
            conditions.append(f"{tier} phase {phase}: {condition}")
    if conditions:
        lines.append("Conditional phases: " + " · ".join(conditions))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "docs" / "agent" / "PIPELINE-MACHINE.md"
    expected = render(json.loads((root / "pipeline-machine.json").read_text(encoding="utf-8")))
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != expected:
            print("FAIL: docs/agent/PIPELINE-MACHINE.md is stale; run scripts/render-pipeline-views.py")
            return 1
        print("PASS generated pipeline view is current")
        return 0
    output.write_text(expected, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
