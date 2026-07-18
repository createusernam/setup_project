#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test the documented human journey against executable pipeline contracts.
# SCOPE: Cross-check setup runbooks, project templates, machine routes, handoffs, and continuation rules.
# DEPENDS: Python unittest and repository documentation/configuration files.
# END_MODULE_CONTRACT
"""Fail closed when the documented human path drifts from executable setup contracts."""

from __future__ import annotations

import json
import fnmatch
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HumanJourneyIntegrityTests(unittest.TestCase):
    def test_runbook_ownership_and_cross_cli_entry_are_unambiguous(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        setup = (ROOT / "docs/human/SETUP.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "docs/human/PIPELINE.md").read_text(encoding="utf-8")
        self.assertNotIn("git clone https://github.com/createusernam/setup", readme)
        self.assertNotIn("git clone https://github.com/createusernam/setup", pipeline)
        self.assertIn("git clone https://github.com/createusernam/setup", setup)
        self.assertIn("single source of truth for installing", setup)
        self.assertIn("Claude Code, Codex, OpenCode, or the terminal/API", pipeline)
        self.assertIn("Human operator path", pipeline)
        self.assertIn("Everyday use: ask the agent", pipeline)
        self.assertIn("What stage are we at, and what should we do next?", pipeline)
        self.assertIn("pipeline-status", readme)
        self.assertIn("setup-pipeline bootstrap", pipeline)
        self.assertIn("setup-preflight 7 . --completion", pipeline)

    def test_portable_docs_do_not_encode_claude_invocation_syntax(self) -> None:
        for relative in (
            "docs/human/PIPELINE.md",
            "docs/human/ARCHITECTURE-GUIDE.md",
            "templates/project/product_brief.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"`/[a-z]", text), relative)
        setup = (ROOT / "docs/human/SETUP.md").read_text(encoding="utf-8")
        for runtime in ("Claude Code", "Codex", "OpenCode", "Terminal/API"):
            self.assertIn(runtime, setup)

    def test_conversational_status_is_portable_and_ledger_backed(self) -> None:
        routing = (ROOT / "docs/agent/SKILL-ROUTING.md").read_text(encoding="utf-8")
        template = (ROOT / "templates/project/CLAUDE.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "docs/human/PIPELINE.md").read_text(encoding="utf-8")
        workctl = (ROOT / "docs/human/WORKCTL.md").read_text(encoding="utf-8")
        skill = (ROOT / "skills/pipeline-status/SKILL.md").read_text(encoding="utf-8")
        for text in (routing, template, skill):
            self.assertIn("pipeline-status", text)
            self.assertIn(".pipeline-state.json", text)
            self.assertIn("preflight", text)
            self.assertIn("never infer", text.lower())
        self.assertIn("READY, BLOCKED, or COMPLETE", pipeline)
        self.assertIn("Do you need workctl?", workctl)
        self.assertIn("no workctl task is created", workctl)
        self.assertIn("Do not mutate the ledger", skill)

    def test_every_human_input_has_values_or_a_discovery_owner(self) -> None:
        setup = (ROOT / "docs/human/SETUP.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "docs/human/PIPELINE.md").read_text(encoding="utf-8")
        compat = (ROOT / "docs/agent/COMPAT.md").read_text(encoding="utf-8")
        self.assertIn("setup-pipeline values", pipeline)
        self.assertIn("schema paths", pipeline)
        self.assertIn("set-condition research_required true", pipeline)
        self.assertIn("set-condition frontend false", pipeline)
        self.assertIn("T0|T1|T2|T3|T4", pipeline)
        self.assertIn("draft|ready|approved|complete", pipeline)
        self.assertIn("contract_locked`, `viz_before_tickets`, and `human_acceptance", pipeline)
        self.assertIn("Find an exact model ID", setup)
        self.assertIn("Allowed values", compat)

    def test_machine_phases_conditions_and_final_gate_match_the_ledger(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        routing = json.loads((ROOT / "model-routing.json").read_text(encoding="utf-8"))
        ledger = json.loads((ROOT / "templates/project/.pipeline-state.json").read_text(encoding="utf-8"))
        self.assertEqual(set(machine["transitions"]), set(routing["phases"]))
        self.assertEqual(ledger["phase"], "-1")
        self.assertIsNone(ledger["policy"]["risk_tier"])
        self.assertEqual(set(ledger["policy"]["conditions"]), {"research_required", "frontend"})
        self.assertEqual(machine["transitions"]["0"]["when"], {"condition": "research_required", "equals": True})
        self.assertEqual(machine["transitions"]["3"]["when"], {"condition": "frontend", "equals": True})
        self.assertNotIn("human_gate", machine["transitions"]["7"])
        self.assertEqual(machine["transitions"]["7"]["completion"]["human_gate"], "human_acceptance")
        serialized = json.dumps(machine) + json.dumps(ledger)
        self.assertNotIn("skipped_gates", serialized)
        self.assertNotIn("skip_contract", serialized)

    def test_atomic_entry_and_phase_exit_contract_are_global(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        template = (ROOT / "templates/project/CLAUDE.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "docs/human/PIPELINE.md").read_text(encoding="utf-8")
        startup = (ROOT / "skills/startup/SKILL.md").read_text(encoding="utf-8")

        for text in (agents, template, pipeline):
            self.assertIn("continue_now", text)
            self.assertIn("waiting_for_human", text)
            self.assertIn("setup-pipeline enter", text)
        self.assertNotIn("setup-pipeline set-phase PHASE", pipeline)
        self.assertIn("PARTIALLY_CONFIGURED", startup)
        self.assertNotIn("ask the agent what stage", startup)

    def test_machine_handoffs_have_template_schema_and_producer(self) -> None:
        handoffs = {
            "risk-review.json": "risk-review",
            "rollout-plan.json": "risk-review",
            "issues-manifest.json": "to-issues",
            "scaffold-manifest.json": "scaffold",
            "build-evidence.json": "tdd",
        }
        for artifact, producer in handoffs.items():
            template = ROOT / "templates/project" / artifact
            schema = template.with_name(template.stem + ".schema.json")
            skill = ROOT / "skills" / producer / "SKILL.md"
            self.assertTrue(template.is_file(), artifact)
            self.assertTrue(schema.is_file(), artifact)
            self.assertIn(artifact, skill.read_text(encoding="utf-8"), producer)
            self.assertEqual(json.loads(template.read_text(encoding="utf-8"))["$schema"], f"./{schema.name}")

        build_loop = (ROOT / "skills/build-loop/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("build-evidence.json", build_loop)
        judge = (ROOT / "skills/judge/SKILL.md").read_text(encoding="utf-8")
        review = (ROOT / "skills/code-review-expert/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("judge-report.json", judge)
        self.assertIn("feature-judge-report.json", judge)
        self.assertIn("code-review.md", review)

    def test_every_machine_artifact_has_one_producer_phase(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        referenced = {
            requirement["artifact"]
            for transition in machine["transitions"].values()
            for requirement in transition.get("requires", []) + transition.get("completion", {}).get("requires", [])
        }
        referenced.update(machine["invalidations"])
        referenced.update(consumer for consumers in machine["invalidations"].values() for consumer in consumers)
        owners = machine["artifact_owners"]
        missing = sorted(
            artifact for artifact in referenced if not any(fnmatch.fnmatch(artifact, pattern) for pattern in owners)
        )
        self.assertEqual(missing, [], f"machine artifacts without producer phase: {missing}")
        self.assertEqual(set(machine["gate_owners"]), {"contract_locked", "viz_before_tickets", "human_acceptance"})


if __name__ == "__main__":
    unittest.main()
