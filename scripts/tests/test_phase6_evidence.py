#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test the trusted read-only semantic exit validator for Phase 6 evidence.
# SCOPE: Exercise contract coverage and completion invariants in isolated temporary projects.
# DEPENDS: Python unittest and skills/build-loop/scripts/validate-phase6.py.
# END_MODULE_CONTRACT
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "skills" / "build-loop" / "scripts" / "validate-phase6.py"
BUILD_EVIDENCE_SCHEMA = ROOT / "templates" / "project" / "build-evidence.schema.json"
PROCESS_DESCRIPTOR = ROOT / "skills" / "build-loop" / "pipeline-validator.json"
DASHBOARD_RENDERER = ROOT / "skills" / "visualization" / "scripts" / "render-iteration-dashboard.py"
SCHEMA_SPEC = importlib.util.spec_from_file_location("phase6_json_schema", ROOT / "scripts" / "json_schema.py")
assert SCHEMA_SPEC and SCHEMA_SPEC.loader
schema_validator = importlib.util.module_from_spec(SCHEMA_SPEC)
SCHEMA_SPEC.loader.exec_module(schema_validator)
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("phase6_preflight", ROOT / "scripts" / "pipeline_preflight.py")
assert PREFLIGHT_SPEC and PREFLIGHT_SPEC.loader
preflight = importlib.util.module_from_spec(PREFLIGHT_SPEC)
PREFLIGHT_SPEC.loader.exec_module(preflight)
DEBT_TYPES = [
    "new_todo_fixme", "suppression", "skipped_test", "dependency_addition",
    "dead_unreachable_code", "duplication", "public_api_growth", "contract_anchor_drift",
    "test_without_criterion_ref", "criterion_without_executable_evidence",
]


class Phase6EvidenceTests(unittest.TestCase):
    def review_document(self) -> dict:
        return {
            "$schema": "./iteration-review.schema.json", "version": "1",
            "producer": "trusted-phase6-orchestrator",
            "consumers": ["phase6-semantic-validator", "iteration-dashboard-renderer", "phase7-review"],
            "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1",
            "worker": {"sequence": 1, "model_id": "model/worker", "context_id": "ctx-worker", "handoff_ref": "reviews/worker.json"},
            "mechanical": {"sequence": 2, "verdict": "PASS", "budget_ref": "iteration-budget.json", "scaffold_integrity_ref": "scaffold-integrity.json"},
            "architect": {"sequence": 3, "model_id": "model/architect", "context_id": "ctx-architect", "verdict": "PASS", "review_ref": "reviews/architect.json", "checks": {"one_leaf": True, "boundaries_interfaces": True, "requirements_delta": True, "debt_delta": True, "explanation_matches_evidence": True}},
            "test_owner": {"sequence": 4, "model_id": "model/test", "context_id": "ctx-test", "fresh_context": True, "verdict": "PASS", "review_ref": "reviews/test-owner.json"},
            "acceptor": {"sequence": 5, "model_id": "model/acceptor", "context_id": "ctx-acceptor", "fresh_context": True, "isolated_context": True, "verdict": "PASS", "review_ref": "reviews/acceptor.json"},
        }

    def integrity_document(self, *, verdict: str = "PASS") -> dict:
        return {
            "$schema": "./scaffold-integrity.schema.json", "version": "1",
            "producer": "trusted-scaffold-integrity-checker",
            "consumers": ["phase6-semantic-validator", "architect-review", "iteration-dashboard-renderer"],
            "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "baseline_commit": "0" * 40,
            "verdict": verdict, "baseline_anchor_hashes": {}, "current_anchor_hashes": {},
            "violations": [],
            "gap": None if verdict != "CONTRACT_GAP" else {
                "type": "architecture_gap", "owning_phase": "5.5", "reason": "Re-attest scaffold.",
            },
        }

    def budget_document(self, *, verdict: str = "PASS", issue_id: str = "ISSUE-1", pbs_leaf: str = "PBS-LEAF-1") -> dict:
        empty = {"files": 0, "added": 0, "deleted": 0, "changed_loc": 0}
        metric = lambda target, maximum: {
            "actual": 0, "target": target, "max": maximum,
            "target_exceeded": False, "hard_max_exceeded": False,
        }
        return {
            "$schema": "./iteration-budget.schema.json", "version": "1",
            "producer": "trusted-iteration-budget-checker",
            "consumers": ["phase6-semantic-validator", "iteration-dashboard-renderer"],
            "issue_id": issue_id, "pbs_leaf": pbs_leaf, "baseline_commit": "0" * 40,
            "verdict": verdict, "changed_files": [], "observed_pbs_leaves": [pbs_leaf],
            "metrics": {name: dict(empty) for name in ("production", "tests", "docs", "generated", "vendor", "lock")},
            "budget": {
                "production_loc": metric(200, 400), "total_loc": metric(400, 800),
                "files": metric(6, 10), "public_interfaces": metric(1, 2),
            },
            "scope_breaches": [],
            "split_reasons": [] if verdict == "PASS" else ["total_loc_max"],
        }

    def run_validator(
        self, contract: dict, evidence: dict, *, set_contract_sha: bool = True,
        iteration_overrides: dict | None = None, tamper_iteration_contract: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            contract_bytes = (json.dumps(contract) + "\n").encode()
            (project / "contract.json").write_bytes(contract_bytes)
            if set_contract_sha:
                evidence["contract_sha256"] = hashlib.sha256(contract_bytes).hexdigest()
            (project / "build-evidence.json").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            budget = self.budget_document()
            (project / "iteration-budget.json").write_text(json.dumps(budget) + "\n", encoding="utf-8")
            (project / "scaffold-integrity.json").write_text(
                json.dumps(self.integrity_document()) + "\n", encoding="utf-8"
            )
            (project / "iteration-review.json").write_text(json.dumps(self.review_document()) + "\n", encoding="utf-8")
            (project / "tests.log").write_text("test evidence\n", encoding="utf-8")
            (project / "architect-review.json").write_text("{}\n", encoding="utf-8")
            for ref in ("reviews/worker.json", "reviews/architect.json", "reviews/test-owner.json", "reviews/acceptor.json"):
                path = project / ref
                path.parent.mkdir(exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
            (project / "model-bindings.json").write_text(json.dumps({"bindings": {
                "reasoning_high": {"enabled": True, "model_id": "model/architect"},
                "implementation_general": {"enabled": True, "model_id": "model/worker"},
                "review_test": {"enabled": True, "model_id": "model/test"},
                "review_acceptance": {"enabled": True, "model_id": "model/acceptor"},
            }}) + "\n", encoding="utf-8")
            iteration = {
                "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "baseline_commit": "0" * 40,
                "goal": "Validate one bounded leaf.", "story_refs": ["US-1"],
                "criterion_refs": [item["id"] for item in contract.get("criteria", [])],
                "verify_commands": ["test"],
                "models": {"architect": "model/architect", "worker": "model/worker", "test_owner": "model/test", "acceptor": "model/acceptor"},
            }
            iteration.update(iteration_overrides or {})
            (project / "iteration-contract.json").write_text(json.dumps(iteration) + "\n", encoding="utf-8")
            story_index = project / "docs" / "stories" / "index.json"
            story_index.parent.mkdir(parents=True)
            story_index.write_text(json.dumps({
                "version": "1",
                "stories": [{
                    "id": "US-1",
                    "use_cases": [{"id": "UC-1", "criterion_refs": iteration["criterion_refs"]}],
                }],
            }) + "\n", encoding="utf-8")
            for command in (
                ("git", "init", "-q"),
                ("git", "config", "user.email", "tests@example.invalid"),
                ("git", "config", "user.name", "Phase6 Tests"),
                ("git", "add", "iteration-contract.json"),
                ("git", "commit", "-qm", "iteration contract"),
            ):
                subprocess.run(command, cwd=project, text=True, capture_output=True, check=True)
            if tamper_iteration_contract:
                iteration["goal"] = "Silently expanded goal."
                (project / "iteration-contract.json").write_text(json.dumps(iteration) + "\n", encoding="utf-8")
            (project / "SUPERVISION.md").write_text(
                "# Supervision\n\n- [Current iteration dashboard](dashboard.md)\n", encoding="utf-8"
            )
            rendered = subprocess.run(
                ["python3", str(DASHBOARD_RENDERER), "--project", str(project)],
                text=True, capture_output=True, check=False,
            )
            if rendered.returncode != 0:
                raise AssertionError(rendered.stdout + rendered.stderr)
            return subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)],
                text=True,
                capture_output=True,
                check=False,
            )

    def complete_evidence(self) -> dict:
        return {
            "$schema": "./build-evidence.schema.json",
            "version": "1",
            "status": "complete",
            "route": "build-loop",
            "contract_ref": "contract.json",
            "contract_sha256": None,
            "issue_id": "ISSUE-1",
            "pbs_leaf": "PBS-LEAF-1",
            "iteration_budget_ref": "iteration-budget.json",
            "iteration_review_ref": "iteration-review.json",
            "iteration_dashboard_json_ref": "iteration-dashboard.json",
            "iteration_dashboard_ref": "iterations/ISSUE-1/dashboard.md",
            "checks": [{"command": "test", "status": "pass", "evidence_ref": "tests.log"}],
            "criteria": [{"id": "C1", "status": "PASS", "evidence_ref": "tests.log"}],
            "trace_refs": [],
            "requirements_delta": {"status": "none", "items": []},
            "debt_delta": {
                "status": "none", "items": [], "reviewed_types": DEBT_TYPES,
                "reviewer": {"role": "architect", "id": "architect@example.test", "evidence_ref": "architect-review.json"},
            },
            "scaffold_integrity": {
                "status": "unchanged", "report_ref": "scaffold-integrity.json",
                "architect_review_ref": None,
            },
            "residual_risks": [],
        }

    def test_complete_evidence_requires_exact_contract_criteria_coverage(self) -> None:
        contract = {
            "criteria": [
                {"id": "C1", "must_pass": True},
                {"id": "C2", "must_pass": False},
            ]
        }
        evidence = self.complete_evidence()

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing criterion evidence: C2", result.stdout)

    def test_complete_evidence_rejects_partial_must_pass(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["criteria"][0]["status"] = "PARTIAL"

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must-pass criterion C1 is PARTIAL", result.stdout)

    def test_complete_evidence_rejects_not_run_check(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["checks"][0]["status"] = "not_run"

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required check 'test' is not_run", result.stdout)

    def test_complete_evidence_requires_existing_safe_evidence_refs(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["checks"][0]["evidence_ref"] = "missing-check.log"
        evidence["criteria"][0]["evidence_ref"] = "../outside.log"

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required check 'test' evidence_ref must name an existing project-relative file", result.stdout)
        self.assertIn("criterion C1 evidence_ref must name an existing project-relative file", result.stdout)

    def test_complete_evidence_requires_exact_verify_command_coverage(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        result = self.run_validator(contract, evidence, iteration_overrides={"verify_commands": ["test", "typecheck"]})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required checks: typecheck", result.stdout)

    def test_complete_evidence_rejects_uncommitted_iteration_contract_changes(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        result = self.run_validator(contract, evidence, tamper_iteration_contract=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("committed", result.stdout)

    def test_complete_evidence_requires_current_contract_sha(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["contract_sha256"] = "0" * 64

        result = self.run_validator(contract, evidence, set_contract_sha=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_sha256 does not match contract.json", result.stdout)

    def test_complete_evidence_requires_leaf_and_dashboard_lineage(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["issue_id"] = ""
        evidence["pbs_leaf"] = None
        evidence["iteration_dashboard_ref"] = "missing-dashboard.md"

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue_id must be non-empty", result.stdout)
        self.assertIn("pbs_leaf must be non-empty", result.stdout)
        self.assertIn("iteration dashboard is missing", result.stdout)

    def test_complete_evidence_requires_closed_requirement_and_debt_deltas(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["requirements_delta"] = {"status": "blocked", "items": []}
        evidence["debt_delta"]["status"] = "blocked"

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirements_delta must be none or resolved", result.stdout)
        self.assertIn("debt_delta must be none, resolved, or accepted", result.stdout)

    def test_scaffold_drift_requires_architect_approval(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["scaffold_integrity"] = {
            "status": "drifted", "report_ref": "scaffold-integrity.json", "architect_review_ref": None,
        }

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scaffold integrity must be unchanged or architect_approved", result.stdout)

    def test_build_evidence_schema_accepts_phase6_completion_fields(self) -> None:
        evidence = self.complete_evidence()
        evidence["$schema"] = "./build-evidence.schema.json"
        evidence["version"] = "1"
        evidence["contract_sha256"] = "0" * 64
        schema = json.loads(BUILD_EVIDENCE_SCHEMA.read_text(encoding="utf-8"))

        self.assertEqual(schema_validator.validate(evidence, schema), [])

    def test_phase6_process_descriptor_is_read_only_and_uses_the_validator(self) -> None:
        descriptor = json.loads(PROCESS_DESCRIPTOR.read_text(encoding="utf-8"))

        self.assertEqual(descriptor["runner"], "python")
        self.assertIs(descriptor["read_only"], True)
        self.assertEqual(descriptor["script"], "scripts/validate-phase6.py")
        self.assertEqual(descriptor["arguments"], ["--project", "{project}"])

    def test_machine_requires_build_loop_phase_process_for_phase6(self) -> None:
        transition = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))["transitions"]["6"]
        self.assertEqual(transition["phase_process"], "build-loop")

        self.assertTrue(preflight.required_phase_process_errors("6", transition, {"phase_processes": {}}))
        self.assertEqual(
            preflight.required_phase_process_errors(
                "6", transition, {"phase_processes": {"6": {"skill": "build-loop"}}}
            ),
            [],
        )

    def test_duplicate_build_evidence_criterion_id_fails_closed(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["criteria"].append({"id": "C1", "status": "PASS", "evidence_ref": "other.log"})

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate build criterion id: C1", result.stdout)

    def test_complete_evidence_rejects_nonpassing_or_mismatched_iteration_budget(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            contract_bytes = (json.dumps(contract) + "\n").encode()
            (project / "contract.json").write_bytes(contract_bytes)
            evidence["contract_sha256"] = hashlib.sha256(contract_bytes).hexdigest()
            (project / "build-evidence.json").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            budget = self.budget_document(
                verdict="SPLIT_REQUIRED", issue_id="ISSUE-OTHER", pbs_leaf="PBS-LEAF-2"
            )
            (project / "iteration-budget.json").write_text(json.dumps(budget) + "\n", encoding="utf-8")
            (project / "scaffold-integrity.json").write_text(
                json.dumps(self.integrity_document()) + "\n", encoding="utf-8"
            )
            (project / "iteration-contract.json").write_text(json.dumps({
                "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "baseline_commit": "0" * 40,
            }) + "\n", encoding="utf-8")
            dashboard = project / "iterations" / "ISSUE-1" / "dashboard.md"
            dashboard.parent.mkdir(parents=True)
            dashboard.write_text("# dashboard\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)],
                text=True, capture_output=True, check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("iteration budget verdict must be PASS", result.stdout)
        self.assertIn("iteration budget issue_id does not match build evidence", result.stdout)
        self.assertIn("iteration budget pbs_leaf does not match build evidence", result.stdout)

    def test_machine_registers_iteration_budget_as_phase6_output_and_phase7_input(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))

        owner = machine["artifact_owners"]["iteration-budget.json"]
        self.assertEqual(owner["producer_phase"], "6")
        self.assertEqual(owner["schema"], "templates/project/iteration-budget.schema.json")
        self.assertIn(
            {"artifact": "iteration-budget.json", "attested": True, "json_pointer": "/verdict", "equals": "PASS", "tiers": ["T2", "T3", "T4"]},
            machine["transitions"]["7"]["requires"],
        )
        self.assertIn("iteration-budget.json", machine["invalidations"]["iteration-contract.json"])

    def test_complete_evidence_rejects_contract_gap_integrity_report(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            contract_bytes = (json.dumps(contract) + "\n").encode()
            (project / "contract.json").write_bytes(contract_bytes)
            evidence["contract_sha256"] = hashlib.sha256(contract_bytes).hexdigest()
            (project / "build-evidence.json").write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            (project / "iteration-budget.json").write_text(json.dumps(self.budget_document()) + "\n", encoding="utf-8")
            (project / "scaffold-integrity.json").write_text(
                json.dumps(self.integrity_document(verdict="CONTRACT_GAP")) + "\n", encoding="utf-8"
            )
            (project / "iteration-contract.json").write_text(json.dumps({
                "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "baseline_commit": "0" * 40,
            }) + "\n", encoding="utf-8")
            dashboard = project / "iterations" / "ISSUE-1" / "dashboard.md"
            dashboard.parent.mkdir(parents=True)
            dashboard.write_text("# dashboard\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)], text=True, capture_output=True, check=False
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scaffold integrity CONTRACT_GAP must return to Phase 5.5", result.stdout)

    def test_machine_registers_integrity_report_as_phase6_output_and_phase7_input(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))

        owner = machine["artifact_owners"]["scaffold-integrity.json"]
        self.assertEqual(owner["producer_phase"], "6")
        self.assertEqual(owner["schema"], "templates/project/scaffold-integrity.schema.json")
        self.assertIn(
            {"artifact": "scaffold-integrity.json", "attested": True, "json_pointer": "/verdict", "in": ["PASS", "SCAFFOLD_DRIFT"], "tiers": ["T2", "T3", "T4"]},
            machine["transitions"]["7"]["requires"],
        )
        self.assertIn("scaffold-integrity.json", machine["invalidations"]["iteration-contract.json"])

    def test_material_requirement_gap_cannot_be_closed_by_worker(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["requirements_delta"] = {
            "status": "resolved",
            "items": [{
                "id": "REQ-1", "type": "implementation_assumption", "material": True,
                "description": "Assume a boundary.",
                "resolution": {
                    "status": "accepted", "authority_role": "worker", "authority_id": "worker/model",
                    "owning_phase": "6", "evidence_ref": "handoff.json",
                },
            }],
        }

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("material requirement gap REQ-1 cannot be resolved by worker", result.stdout)

    def test_requirement_gap_types_enforce_authority_and_upstream_route(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["requirements_delta"] = {
            "status": "resolved",
            "items": [
                {"id": "REQ-A", "type": "architecture_gap", "material": True, "description": "Boundary missing.",
                 "resolution": {"status": "accepted", "authority_role": "architect", "authority_id": "arch", "owning_phase": "6", "evidence_ref": "review.json"}},
                {"id": "REQ-P", "type": "product_gap", "material": True, "description": "Behavior missing.",
                 "resolution": {"status": "returned_upstream", "authority_role": "architect", "authority_id": "arch", "owning_phase": "2b", "evidence_ref": "review.json"}},
                {"id": "REQ-E", "type": "evidence_gap", "material": True, "description": "Proof missing.",
                 "resolution": {"status": "accepted", "authority_role": "architect", "authority_id": "arch", "owning_phase": "6", "evidence_ref": "review.json"}},
            ],
        }

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("architecture_gap REQ-A must return to Phase 2b", result.stdout)
        self.assertIn("product_gap REQ-P requires product_owner authority", result.stdout)
        self.assertIn("evidence_gap REQ-E must return to research/prototype or be accepted_risk", result.stdout)

    def test_architect_may_accept_implementation_assumption(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["requirements_delta"] = {
            "status": "resolved",
            "items": [{
                "id": "REQ-OK", "type": "implementation_assumption", "material": False,
                "description": "Use the existing internal helper.",
                "resolution": {"status": "accepted", "authority_role": "architect", "authority_id": "arch", "owning_phase": "6", "evidence_ref": "architect-review.json"},
            }],
        }

        result = self.run_validator(contract, evidence)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_accepted_debt_requires_identity_reason_and_follow_up(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["debt_delta"].update({
            "status": "accepted",
            "items": [{
                "id": "DEBT-1", "type": "suppression", "description": "Temporary ignore.",
                "resolution": {"status": "owner_accepted", "owner_id": "", "reason": "", "follow_up_task": "", "evidence_ref": ""},
            }],
        })

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner-accepted debt DEBT-1 requires owner_id, reason, follow_up_task, and evidence_ref", result.stdout)

    def test_debt_review_must_cover_every_category_exactly(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        evidence = self.complete_evidence()
        evidence["debt_delta"]["reviewed_types"] = ["new_todo_fixme"]

        result = self.run_validator(contract, evidence)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("debt reviewed_types must exactly cover", result.stdout)

    def test_removed_or_fully_owner_accepted_debt_can_complete(self) -> None:
        contract = {"criteria": [{"id": "C1", "must_pass": True}]}
        for status, resolution in (
            ("resolved", {"status": "removed", "owner_id": "", "reason": "", "follow_up_task": "", "evidence_ref": "fix.diff"}),
            ("accepted", {"status": "owner_accepted", "owner_id": "owner@example.test", "reason": "Bounded migration debt.", "follow_up_task": "ISSUE-2", "evidence_ref": "owner-decision.json"}),
        ):
            with self.subTest(status=status):
                evidence = self.complete_evidence()
                evidence["debt_delta"].update({
                    "status": status,
                    "items": [{"id": "DEBT-OK", "type": "duplication", "description": "Known duplicate.", "resolution": resolution}],
                })

                result = self.run_validator(contract, evidence)

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
