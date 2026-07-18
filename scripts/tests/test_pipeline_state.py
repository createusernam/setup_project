#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test human pipeline ledger initialization, attestation, invalidation, and signing.
# SCOPE: Exercise pipeline-state.py against a temporary project without external dependencies.
# DEPENDS: Python standard library and scripts/pipeline-state.py.
# END_MODULE_CONTRACT
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("pipeline_state", ROOT / "scripts" / "pipeline-state.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


# START_BLOCK_PIPELINE_STATE_CASES
class PipelineStateTests(unittest.TestCase):
    def test_bootstrap_adopts_existing_project_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            existing = project / "CLAUDE.md"
            existing.write_text("existing rules\n", encoding="utf-8")
            module.command_bootstrap(SimpleNamespace(), ROOT, project)
            self.assertEqual(existing.read_text(encoding="utf-8"), "existing rules\n")
            self.assertTrue((project / ".pipeline-state.json").is_file())
            self.assertTrue((project / "build-evidence.schema.json").is_file())
            self.assertTrue((project / "AGENTS.md").is_symlink())

    def test_new_ledger_defers_route_and_status_does_not_offer_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            ledger = json.loads((project / ".pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["phase"], "-1")
            self.assertIsNone(ledger["policy"]["risk_tier"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.command_status(SimpleNamespace(), ROOT, project)
            rendered = output.getvalue()
            self.assertIn("current stage: -1 — discovery process", rendered)
            self.assertIn("complete discovery artifacts", rendered)
            self.assertIn("current check: setup-preflight -1", rendered)
            self.assertNotIn("next entry check", rendered)

    def test_values_lists_human_inputs_and_schema_owners(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.command_values(SimpleNamespace(), ROOT, ROOT)
        rendered = output.getvalue()
        self.assertIn("phases: -1, 0, 1, 2", rendered)
        self.assertIn("risk tiers:", rendered)
        self.assertIn("human gates:", rendered)
        self.assertIn("human request contracts:", rendered)
        self.assertIn("model_bindings: authority=project_owner, response=file", rendered)
        self.assertIn("route conditions: research_required=true|false, frontend=true|false", rendered)
        self.assertIn("artifact statuses:", rendered)
        self.assertIn("runtimes: claude, codex, opencode", rendered)
        self.assertIn("evidence-handoff values:", rendered)
        self.assertIn("risk-review.schema.json", rendered)

    def test_conditions_make_the_selected_route_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            module.command_set_condition(SimpleNamespace(condition="research_required", value="true"), ROOT, project)
            module.command_set_condition(SimpleNamespace(condition="frontend", value="false"), ROOT, project)
            module.command_set_tier(SimpleNamespace(tier="T3", reason="cross-module"), ROOT, project)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.command_status(SimpleNamespace(), ROOT, project)
            rendered = output.getvalue()
            self.assertIn("route: -1 -> 0 -> 1 -> 2 -> 2-PM -> 2b -> 4", rendered)
            self.assertNotIn("-> 3 ->", rendered)

            ledger_path = project / ".pipeline-state.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["phase"] = "2"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.command_status(SimpleNamespace(), ROOT, project)
            rendered = output.getvalue()
            self.assertIn("current stage: 2 — planning-with-files", rendered)
            self.assertIn("next phase: 2-PM", rendered)
            self.assertIn("transition: waiting_for_human", rendered)
            self.assertIn("human request: model_bindings", rendered)
            self.assertIn("authority: project_owner", rendered)
            self.assertIn(str(project / "model-bindings.json"), rendered)
            self.assertIn(str(project / "model-bindings.schema.json"), rendered)
            self.assertIn(str(ROOT / "docs/agent/COMPAT.md"), rendered)
            self.assertIn("response format: file", rendered)
            self.assertIn("missing profiles:", rendered)

            (project / "task_plan.md").write_text("plan\n", encoding="utf-8")
            module.command_attest(SimpleNamespace(artifacts=["task_plan.md"], status="ready"), ROOT, project)
            ledger_path = project / ".pipeline-state.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["phase"] = "4b"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            module.command_sign(SimpleNamespace(gate="contract_locked", by="owner"), ROOT, project)
            module.command_set_condition(SimpleNamespace(condition="frontend", value="true"), ROOT, project)
            ledger = json.loads((project / ".pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["status"], "invalidated")
            self.assertIsNone(ledger["human_gates"]["contract_locked"]["by"])
            self.assertEqual(ledger["phase"], "-1")

    def test_human_gate_wait_renders_inline_response_and_evidence_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            request = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))[
                "human_requests"
            ]["viz_before_tickets"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.render_human_request(
                    ROOT,
                    project,
                    "viz_before_tickets",
                    request,
                    context=["human_gate: viz_before_tickets requires by and at"],
                )
            rendered = output.getvalue()
            self.assertIn("human request: viz_before_tickets", rendered)
            self.assertIn("authority: product_owner", rendered)
            self.assertIn(str(project / "SUPERVISION.md"), rendered)
            self.assertIn("response format: inline", rendered)
            self.assertIn('"action": "approve|revise"', rendered)
            self.assertIn("consequences:", rendered)
            self.assertIn("resume:", rendered)

    def test_atomic_enter_rejects_a_jump_and_preserves_ledger_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            ledger_path = project / ".pipeline-state.json"
            before = ledger_path.read_bytes()

            with self.assertRaisesRegex(ValueError, "route|next|classification"):
                module.command_enter(SimpleNamespace(phase="3"), ROOT, project)

            self.assertEqual(ledger_path.read_bytes(), before)

    def test_atomic_enter_commits_only_after_target_preflight_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_bootstrap(SimpleNamespace(), ROOT, project)
            (project / "product_brief.md").write_text("# Approved brief\n", encoding="utf-8")
            (project / "evidence-handoff.json").write_text(
                json.dumps({"decision": "delivery", "spec_gaps": []}) + "\n", encoding="utf-8"
            )
            (project / "business_model.md").write_text("# Approved business model\n", encoding="utf-8")
            module.command_attest(
                SimpleNamespace(
                    artifacts=["product_brief.md", "evidence-handoff.json", "business_model.md"],
                    status="approved",
                ),
                ROOT,
                project,
            )
            bindings_path = project / "model-bindings.json"
            bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
            bindings["bindings"]["reasoning_balanced"] = {
                "runtime": "codex", "model_id": "provider/reasoning-balanced", "enabled": True
            }
            bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
            module.command_set_condition(SimpleNamespace(condition="research_required", value="false"), ROOT, project)
            module.command_set_condition(SimpleNamespace(condition="frontend", value="false"), ROOT, project)
            module.command_set_tier(SimpleNamespace(tier="T2", reason="small reversible feature"), ROOT, project)

            module.command_enter(SimpleNamespace(phase="1"), ROOT, project)
            ledger = json.loads((project / ".pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["phase"], "1")
            self.assertEqual(module.command_guard(SimpleNamespace(phase="1"), ROOT, project), 0)

            ledger["phase"] = "7"
            (project / ".pipeline-state.json").write_text(json.dumps(ledger), encoding="utf-8")
            module.command_enter(SimpleNamespace(phase="1"), ROOT, project)
            reworked = json.loads((project / ".pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(reworked["phase"], "1")

    def test_status_reports_actual_next_phase_and_model_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_bootstrap(SimpleNamespace(), ROOT, project)
            module.command_set_condition(SimpleNamespace(condition="research_required", value="false"), ROOT, project)
            module.command_set_condition(SimpleNamespace(condition="frontend", value="false"), ROOT, project)
            module.command_set_tier(SimpleNamespace(tier="T3", reason="cross-module"), ROOT, project)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.command_status(SimpleNamespace(), ROOT, project)
            rendered = output.getvalue()
            self.assertIn("next phase: 1", rendered)
            self.assertIn("model routing: UNCONFIGURED", rendered)
            self.assertIn("next action: configure required model profiles", rendered)

    def test_provisional_research_can_enter_before_final_tier_selection(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_bootstrap(SimpleNamespace(), ROOT, project)
            (project / "product_brief.md").write_text("# Discovery brief\n", encoding="utf-8")
            (project / "evidence-handoff.json").write_text(json.dumps({"decision": "alpha"}) + "\n", encoding="utf-8")
            module.command_attest(
                SimpleNamespace(artifacts=["product_brief.md", "evidence-handoff.json"], status="ready"), ROOT, project
            )
            bindings_path = project / "model-bindings.json"
            bindings = json.loads(bindings_path.read_text(encoding="utf-8"))
            bindings["bindings"]["reasoning_balanced"] = {
                "runtime": "codex", "model_id": "provider/reasoning-balanced", "enabled": True
            }
            bindings["bindings"]["research_worker"] = {
                "runtime": "codex", "model_id": "provider/research-worker", "enabled": True
            }
            bindings_path.write_text(json.dumps(bindings), encoding="utf-8")
            module.command_set_condition(SimpleNamespace(condition="research_required", value="true"), ROOT, project)

            module.command_enter(SimpleNamespace(phase="0"), ROOT, project)
            ledger = json.loads((project / ".pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["phase"], "0")
            self.assertIsNone(ledger["policy"]["risk_tier"])

    def test_status_surfaces_premature_artifact_as_current_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_bootstrap(SimpleNamespace(), ROOT, project)
            (project / "design-contract.json").write_text("{}\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.command_status(SimpleNamespace(), ROOT, project)
            rendered = output.getvalue()
            self.assertIn("readiness: BLOCKED", rendered)
            self.assertIn("artifact_ownership", rendered)
            self.assertIn("resolve the listed current-phase blockers", rendered)

    def test_migrate_upgrades_legacy_v2_ledger_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            legacy = {
                "version": "2",
                "phase": "discovery",
                "policy": {"risk_tier": None, "skipped_gates": []},
                "artifacts": {"product_brief.md": {"sha256": None}},
                "human_gates": {"stakeholder_input_confirmed": {"by": None, "at": None}},
                "model_bindings_file": "model-bindings.json",
            }
            (project / ".pipeline-state.json").write_text(json.dumps(legacy), encoding="utf-8")
            module.command_migrate(SimpleNamespace(), ROOT, project)
            migrated = json.loads((project / ".pipeline-state.json").read_text(encoding="utf-8"))
            self.assertEqual(migrated["phase"], "-1")
            self.assertEqual(set(migrated["policy"]["conditions"]), {"research_required", "frontend"})
            self.assertNotIn("skipped_gates", migrated["policy"])
            self.assertNotIn("stakeholder_input_confirmed", migrated["human_gates"])
            self.assertTrue(list(project.glob(".pipeline-state.json.bak-*")))

    def test_attest_change_invalidates_consumers_and_signs_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            (project / "product_brief.md").write_text("v1\n", encoding="utf-8")
            (project / "task_plan.md").write_text("plan\n", encoding="utf-8")

            module.command_attest(SimpleNamespace(artifacts=["product_brief.md"], status="ready"), ROOT, project)
            ledger_path = project / ".pipeline-state.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["phase"] = "2"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            module.command_attest(SimpleNamespace(artifacts=["task_plan.md"], status="ready"), ROOT, project)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["status"], "ready")

            (project / "product_brief.md").write_text("v2\n", encoding="utf-8")
            ledger["phase"] = "-1"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            module.command_attest(SimpleNamespace(artifacts=["product_brief.md"], status="approved"), ROOT, project)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["status"], "invalidated")
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["invalidated_by"], "product_brief.md")

            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["phase"] = "4b"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            module.command_sign(SimpleNamespace(gate="contract_locked", by="owner@example.test"), ROOT, project)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["human_gates"]["contract_locked"]["by"], "owner@example.test")

            (project / "product_brief.md").write_text("v3\n", encoding="utf-8")
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["phase"] = "-1"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            module.command_attest(SimpleNamespace(artifacts=["product_brief.md"], status="approved"), ROOT, project)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertIsNone(ledger["human_gates"]["contract_locked"]["by"])

    def test_rejects_artifact_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            with self.assertRaisesRegex(ValueError, "inside the project"):
                module.command_attest(SimpleNamespace(artifacts=["../outside"], status="ready"), ROOT, project)
# END_BLOCK_PIPELINE_STATE_CASES


if __name__ == "__main__":
    unittest.main()
