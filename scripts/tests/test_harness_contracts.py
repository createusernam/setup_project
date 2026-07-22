#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test route reachability, schema provenance, conformance gates, memory, and viewpoints.
# SCOPE: Exercise new harness contracts without network calls or external services.
# DEPENDS: Python unittest and repository scripts/templates.
# END_MODULE_CONTRACT
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipeline_state = load("pipeline_state_contracts", ROOT / "scripts/pipeline-state.py")
preflight = load("pipeline_preflight_contracts", ROOT / "scripts/pipeline_preflight.py")
schema = load("json_schema_contracts", ROOT / "scripts/json_schema.py")


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document) + "\n", encoding="utf-8")


class HarnessContractTests(unittest.TestCase):
    # START_BLOCK_ROUTE_AND_AUTHORITY_CONTRACTS
    def test_every_tier_route_is_ordered_and_short_routes_own_evidence(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        phase_order = list(machine["transitions"])
        for tier, policy in machine["risk_policy"]["tiers"].items():
            route = policy["required_phases"]
            self.assertEqual(route, sorted(route, key=phase_order.index), tier)
            self.assertEqual(route[-1], "7", tier)
        self.assertEqual(machine["risk_policy"]["tiers"]["T0"]["required_phases"], ["6f", "7"])
        self.assertEqual(machine["risk_policy"]["tiers"]["T1"]["required_phases"], ["6f", "7"])
        self.assertEqual(machine["artifact_owners"]["build-evidence.json"]["producer_phases"], ["6f", "6"])
        optional = [item for item in machine["transitions"]["1"]["requires"] if item["artifact"] == "business_model.md"]
        self.assertEqual(optional, [{"artifact": "business_model.md", "attested": True, "when_present": True}])

    def test_phase_minus_one_distinguishes_universal_intake_from_tier_route(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        intake = machine["transitions"]["-1"]
        self.assertEqual(intake["entry_mode"], "pre_route")
        self.assertEqual(intake["required_after_classification_for"], ["T3", "T4"])
        generated = (ROOT / "docs" / "agent" / "PIPELINE-MACHINE.md").read_text(encoding="utf-8")
        self.assertIn("universal pre-route intake; required after classification for T3, T4", generated)

    def test_every_tier_terminal_requirement_has_a_producer_on_its_route(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        terminal_requirements = machine["transitions"]["7"]["requires"]
        for tier, policy in machine["risk_policy"]["tiers"].items():
            route = set(policy["required_phases"])
            route.update(policy.get("conditional_phases", {}))
            for requirement in terminal_requirements:
                if tier not in requirement.get("tiers", ["T0", "T1", "T2", "T3", "T4"]):
                    continue
                ownership = machine["artifact_owners"][requirement["artifact"]]
                producers = set(ownership.get("producer_phases") or [ownership.get("producer_phase")])
                self.assertTrue(
                    producers & route,
                    f"{tier} cannot produce terminal requirement {requirement['artifact']} on route {sorted(route)}",
                )

    def test_configured_human_authorities_are_enforced_per_gate(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            write_json(project / "role-assignment.json", {
                "version": "1", "product_owner": "product@example.test",
                "technical_owner": "tech@example.test", "accountable_acceptor": "accept@example.test",
            })
            signature = {
                "by": None, "at": None,
                "approvals": {"product_owner": {"by": "product@example.test", "at": "2026-07-22T00:00:00Z"}},
            }
            failures, configured = preflight.human_authority_errors(
                ROOT, project, "contract_locked", "T3", signature, machine,
                {"artifacts": {"role-assignment.json": {
                    "status": "approved", "sha256": hashlib.sha256((project / "role-assignment.json").read_bytes()).hexdigest()
                }}},
            )
            self.assertTrue(configured)
            self.assertTrue(any("technical_owner" in failure for failure in failures))
            signature["approvals"]["technical_owner"] = {
                "by": "tech@example.test", "at": "2026-07-22T00:00:00Z"
            }
            failures, _ = preflight.human_authority_errors(
                ROOT, project, "contract_locked", "T3", signature, machine,
                {"artifacts": {"role-assignment.json": {
                    "status": "approved", "sha256": hashlib.sha256((project / "role-assignment.json").read_bytes()).hexdigest()
                }}},
            )
            self.assertEqual(failures, [])
    # END_BLOCK_ROUTE_AND_AUTHORITY_CONTRACTS

    # START_BLOCK_ATTESTATION_AND_MODEL_CONTRACTS
    def test_attest_rejects_schema_invalid_bytes_without_ledger_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            pipeline_state.command_bootstrap(SimpleNamespace(), ROOT, project)
            ledger_before = (project / ".pipeline-state.json").read_bytes()
            write_json(project / "evidence-handoff.json", {"decision": "delivery"})
            with self.assertRaisesRegex(ValueError, "schema-invalid"):
                pipeline_state.command_attest(
                    SimpleNamespace(artifacts=["evidence-handoff.json"], status="ready"), ROOT, project
                )
            self.assertEqual((project / ".pipeline-state.json").read_bytes(), ledger_before)

    def test_attestation_records_schema_path_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            pipeline_state.command_bootstrap(SimpleNamespace(), ROOT, project)
            pipeline_state.command_attest(
                SimpleNamespace(artifacts=["evidence-handoff.json"], status="ready"), ROOT, project
            )
            record = json.loads((project / ".pipeline-state.json").read_text())["artifacts"]["evidence-handoff.json"]
            self.assertEqual(record["schema"], "templates/project/evidence-handoff.schema.json")
            expected = hashlib.sha256((ROOT / record["schema"]).read_bytes()).hexdigest()
            self.assertEqual(record["schema_sha256"], expected)

    def test_required_binding_uses_matching_qualified_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            evidence = {
                "$schema": "../model-conformance.schema.json",
                "version": "1",
                "harness_version": "2",
                "profile": "coding_worker",
                "provider": "fixture",
                "runtime": "api",
                "model_id": "fixture/model",
                "endpoint_host": "example.test",
                "executed_at": "2026-07-20T00:00:00Z",
                "settings": {"temperature": 0, "max_tokens": 1, "timeout_seconds": 1, "max_repair_attempts": 0, "thinking": "disabled"},
                "scenarios": [
                    {"id": probe, "critical": True, "status": "pass", "attempts": 1, "latency_ms": 0, "evidence": {}}
                    for probe in (
                        "bounded_patch", "allowed_path_compliance", "compiler_typecheck_feedback",
                        "targeted_test_execution", "scaffold_anchor_preservation", "stop_on_contract_gap",
                        "secret_non_disclosure", "destructive_command_refusal",
                        "untrusted_repository_instruction_resistance", "schema_valid_handoff_dashboard_input",
                        "failure_recovery",
                    )
                ],
                "summary": {"passed": 11, "total": 11, "pass_rate": 1, "threshold": 0.8, "critical_passed": 11, "critical_total": 11, "critical_failures": [], "qualified": True},
                "provenance": {"setup_git_sha": "fixture", "runner_sha256": "0" * 64},
            }
            write_json(project / "model-conformance/fixture.json", evidence)
            binding = {"runtime": "api", "model_id": "fixture/model", "enabled": True, "conformance_ref": "model-conformance/fixture.json"}
            policy = {"mode": "required", "minimum_pass_rate": 0.8, "harness_version": "2"}
            machine = json.loads((ROOT / "pipeline-machine.json").read_text())
            self.assertEqual(preflight.model_conformance_errors(ROOT, project, machine, "implementation_general", binding, policy), [])
            binding["model_id"] = "other/model"
            self.assertTrue(preflight.model_conformance_errors(ROOT, project, machine, "implementation_general", binding, policy))
    # END_BLOCK_ATTESTATION_AND_MODEL_CONTRACTS

    # START_BLOCK_STATE_AND_PLANNING_CONTRACTS
    def test_state_envelope_viewpoint_and_kaeru_contracts(self) -> None:
        valid_documents = {
            "artifact-envelope.schema.json": {
                "schema_version": "1", "artifact_type": "handoff", "project_id": "p", "task_id": None,
                "phase": "6f", "status": "ready", "revision": {"sha256": None, "supersedes": None},
                "provenance": ["git:abc"], "authority": {"producer": "agent", "approver": None},
                "facts": [], "assumptions": [], "unknowns": [], "invariants": [],
                "next_transition": {"allowed": True, "blockers": []},
            },
            "kaeru-memory-ref.schema.json": {
                "$schema": "../kaeru-memory-ref.schema.json", "memory_ref": "kaeru://p/n", "project_id": "p",
                "task_id": None, "kind": "lesson", "status": "supported", "source_refs": ["git:abc"],
                "authority": "agent", "visibility": "private", "valid_at": "2026-07-20T00:00:00Z",
                "recorded_at": "2026-07-20T00:00:00Z",
            },
            "viewpoint.schema.json": {
                "$schema": "../../viewpoint.schema.json", "version": "1", "view_id": "v1", "stakeholder": "owner",
                "decision": "approve capacity", "story_ref": "US-1", "concern": "flow_and_overflow", "scale": "system",
                "focal_elements": ["in", "capacity", "out"], "actors": ["owner"],
                "metaphor": {"name": "bucket", "mapping": {"bucket": "capacity"}, "limits": ["not homogeneous"]},
                "canonical_refs": ["contract.json#/integrations"], "hidden_aggregation": ["priority"],
                "next_scale_views": [], "approval": {"status": "draft", "by": None, "at": None},
            },
        }
        for name, document in valid_documents.items():
            contract = json.loads((ROOT / "templates/project" / name).read_text())
            self.assertEqual(schema.validate(document, contract), [], name)

    def test_planning_json_is_canonical_and_markdown_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = subprocess.run(
                ["python3", str(ROOT / "skills/planning-with-files/scripts/planning-state.py"), "init", str(directory), "--created", "2026-07-20"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((directory / "task_plan.md").read_text().startswith("<!-- GENERATED FROM task_plan.json"))
            self.assertIn("No entries yet", (directory / "progress.md").read_text())
    # END_BLOCK_STATE_AND_PLANNING_CONTRACTS


if __name__ == "__main__":
    unittest.main()
