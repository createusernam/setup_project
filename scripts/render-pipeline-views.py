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
    for phase, transition in transitions.items():
        lines.append(f'    {phase_ids[phase]}["{phase} · {transition["skill"]}"]')
    order = {phase: index for index, phase in enumerate(transitions)}
    edges: dict[tuple[str, str], set[str]] = {}
    for tier, policy in machine["risk_policy"]["tiers"].items():
        route = list(policy["required_phases"])
        # A conditional phase is part of the route only when its predicate is true.  Insert it
        # at its canonical transition position, then render both possibilities as labelled edges.
        for phase in policy.get("conditional_phases", {}):
            insertion = next((index for index, item in enumerate(route) if order[item] > order[phase]), len(route))
            conditional_route = [*route[:insertion], phase, *route[insertion:]]
            for left, right in zip(conditional_route, conditional_route[1:]):
                edges.setdefault((left, right), set()).add(f"{tier} conditional")
        for left, right in zip(route, route[1:]):
            edges.setdefault((left, right), set()).add(tier)
    for (left, right), tiers in sorted(edges.items(), key=lambda item: (order[item[0][0]], order[item[0][1]])):
        label = ", ".join(sorted(tiers))
        lines.append(f"    {phase_ids[left]} -->|{label}| {phase_ids[right]}")
    for phase, transition in transitions.items():
        for verdict, outcome in transition.get("outcomes", {}).items():
            target = outcome.get("next") or outcome.get("return_to")
            if target:
                direction = "next" if "next" in outcome else "return"
                lines.append(f"    {phase_ids[phase]} -. {verdict} ({direction}) .-> {phase_ids[target]}")
            elif outcome.get("stop"):
                lines.append(f'    {phase_ids[phase]} -. {verdict} (stop) .-> STOP["stop"]')
    lines.extend(["```", "", "| Phase | Skill | Tiers | Run when | Entry inputs | Entry gate | Completion |", "|---|---|---|---|---|---|---|"])
    for phase, transition in transitions.items():
        inputs = []
        for requirement in transition.get("requires", []):
            semantic = requirement.get("json_pointer", "")
            expected = requirement.get("equals", requirement.get("in", ""))
            when = requirement.get("when")
            condition = f' when {when["condition"]}={str(when["equals"]).lower()}' if when else ""
            tiers = f' on {"/".join(requirement["tiers"])}' if requirement.get("tiers") else ""
            inputs.append(f'`{requirement["artifact"]}{semantic}` {expected}{condition}{tiers}'.strip())
        completion = transition.get("completion", {})
        completion_inputs = []
        for requirement in completion.get("requires", []):
            semantic = requirement.get("json_pointer", "")
            expected = requirement.get("equals", requirement.get("in", ""))
            when = requirement.get("when")
            condition = f' when {when["condition"]}={str(when["equals"]).lower()}' if when else ""
            tiers = f' on {"/".join(requirement["tiers"])}' if requirement.get("tiers") else ""
            completion_inputs.append(f'`{requirement["artifact"]}{semantic}` {expected}{condition}{tiers}'.strip())
        completion_gate = completion.get("human_gate")
        completion_view = "<br>".join(completion_inputs + ([f"gate `{completion_gate}`"] if completion_gate else [])) or "—"
        when = transition.get("when")
        when_view = f'`{when["condition"]}={str(when["equals"]).lower()}`' if when else "always on selected tier"
        tiers_view = ", ".join(transition["tiers"])
        if transition.get("entry_mode") == "pre_route":
            required = ", ".join(transition.get("required_after_classification_for", []))
            when_view = f"universal pre-route intake; required after classification for {required}"
            tiers_view = f"all before classification; {required} after"
        lines.append(f'| {phase} | `{transition["skill"]}` | {tiers_view} | {when_view} | {"<br>".join(inputs) or "—"} | `{transition.get("human_gate", "—")}` | {completion_view} |')
    lines.extend(["", "Risk policy: " + " · ".join(f"{tier}={data['label']}" for tier, data in machine["risk_policy"]["tiers"].items())])
    conditions = []
    for tier, data in machine["risk_policy"]["tiers"].items():
        for phase, condition in data.get("conditional_phases", {}).items():
            conditions.append(f"{tier} phase {phase}: {condition['condition']}={str(condition['equals']).lower()} — {condition['description']}")
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
