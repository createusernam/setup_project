#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test the ordered Phase 6 mechanical, architect, test-owner, and acceptor chain.
# SCOPE: Validate role duties, exact model bindings, distinct identities, fresh isolation, and machine registration.
# DEPENDS: Python unittest and build-loop iteration review validator.
# END_MODULE_CONTRACT
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "skills" / "build-loop" / "scripts" / "validate-iteration-review.py"


def valid_review() -> dict:
    return {
        "$schema": "./iteration-review.schema.json", "version": "1",
        "producer": "trusted-phase6-orchestrator",
        "consumers": ["phase6-semantic-validator", "iteration-dashboard-renderer", "phase7-review"],
        "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1",
        "worker": {"sequence": 1, "model_id": "model/worker", "context_id": "ctx-worker", "handoff_ref": "reviews/worker.json"},
        "mechanical": {"sequence": 2, "verdict": "PASS", "budget_ref": "iteration-budget.json", "scaffold_integrity_ref": "scaffold-integrity.json"},
        "architect": {
            "sequence": 3, "model_id": "model/architect", "context_id": "ctx-architect",
            "verdict": "PASS", "review_ref": "reviews/architect.json",
            "checks": {"one_leaf": True, "boundaries_interfaces": True, "requirements_delta": True, "debt_delta": True, "explanation_matches_evidence": True},
        },
        "test_owner": {"sequence": 4, "model_id": "model/test", "context_id": "ctx-test", "fresh_context": True, "verdict": "PASS", "review_ref": "reviews/test-owner.json"},
        "acceptor": {"sequence": 5, "model_id": "model/acceptor", "context_id": "ctx-acceptor", "fresh_context": True, "isolated_context": True, "verdict": "PASS", "review_ref": "reviews/acceptor.json"},
    }


class IterationReviewTests(unittest.TestCase):
    def run_validator(self, review: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "iteration-contract.json").write_text(json.dumps({
                "status": "ready", "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1",
                "models": {"architect": "model/architect", "worker": "model/worker", "test_owner": "model/test", "acceptor": "model/acceptor"},
            }) + "\n", encoding="utf-8")
            (project / "model-bindings.json").write_text(json.dumps({"bindings": {
                "reasoning_high": {"enabled": True, "model_id": "model/architect"},
                "implementation_general": {"enabled": True, "model_id": "model/worker"},
                "review_test": {"enabled": True, "model_id": "model/test"},
                "review_acceptance": {"enabled": True, "model_id": "model/acceptor"},
            }}) + "\n", encoding="utf-8")
            for ref in ("reviews/worker.json", "reviews/architect.json", "reviews/test-owner.json", "reviews/acceptor.json"):
                path = project / ref
                path.parent.mkdir(exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
            (project / "iteration-budget.json").write_text('{"verdict":"PASS"}\n', encoding="utf-8")
            (project / "scaffold-integrity.json").write_text('{"verdict":"PASS"}\n', encoding="utf-8")
            (project / "iteration-review.json").write_text(json.dumps(review) + "\n", encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)], text=True, capture_output=True, check=False
            )

    def test_complete_ordered_review_chain_passes(self) -> None:
        result = self.run_validator(valid_review())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_architect_must_check_every_declared_responsibility(self) -> None:
        review = valid_review()
        review["architect"]["checks"]["debt_delta"] = False
        result = self.run_validator(review)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("architect check debt_delta must pass", result.stdout)

    def test_worker_test_owner_and_acceptor_models_are_distinct_and_exact(self) -> None:
        review = valid_review()
        review["test_owner"]["model_id"] = "model/worker"
        result = self.run_validator(review)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("test_owner model does not match iteration contract", result.stdout)
        self.assertIn("worker, test_owner, and acceptor model IDs must be distinct", result.stdout)

    def test_acceptor_requires_fresh_isolated_unique_context(self) -> None:
        review = valid_review()
        review["acceptor"].update({"fresh_context": False, "isolated_context": False, "context_id": "ctx-worker"})
        result = self.run_validator(review)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("acceptor must use a fresh isolated context", result.stdout)
        self.assertIn("review context IDs must be unique", result.stdout)

    def test_sequence_and_stage_verdicts_fail_closed(self) -> None:
        review = valid_review()
        review["architect"]["sequence"] = 4
        review["test_owner"]["verdict"] = "REVISE"
        result = self.run_validator(review)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("review stage sequence must be worker=1, mechanical=2, architect=3, test_owner=4, acceptor=5", result.stdout)
        self.assertIn("test_owner verdict must be PASS", result.stdout)

    def test_machine_and_routing_register_architect_review_chain(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        routing = json.loads((ROOT / "model-routing.json").read_text(encoding="utf-8"))
        self.assertEqual(machine["artifact_owners"]["iteration-review.json"]["producer_phase"], "6")
        self.assertIn(
            {"artifact": "iteration-review.json", "attested": True, "json_pointer": "/acceptor/verdict", "equals": "PASS", "tiers": ["T2", "T3", "T4"]},
            machine["transitions"]["7"]["requires"],
        )
        self.assertEqual(routing["phases"]["6"]["roles"]["architect"], "reasoning_high")
        self.assertEqual(routing["phases"]["6"]["distinct_roles"], [["implementer", "test_owner", "acceptor"]])


if __name__ == "__main__":
    unittest.main()
