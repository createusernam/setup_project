#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test fail-closed supervision between bounded build-loop worker attempts.
# SCOPE: Verify evaluator, mechanical, and architect evidence determine whether another worker may start.
# DEPENDS: Python unittest, verdict.sh, and check-attempt-transition.py.
# END_MODULE_CONTRACT
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "skills" / "build-loop" / "scripts" / "check-attempt-transition.py"


class AttemptTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        iteration = self.project / ".build-loop" / "iterations" / "1"
        iteration.mkdir(parents=True)
        (self.project / ".build-loop" / "iteration-log.json").write_text(
            json.dumps({"iterations": [], "restart_count": 0}) + "\n", encoding="utf-8"
        )
        (self.project / "contract.json").write_text(json.dumps({
            "criteria": [{"id": "c1", "weight": 1, "must_pass": False}],
            "restart_threshold": {"max_iterations": 5, "no_progress_iterations": 3, "criteria_floor": 0.4}
        }) + "\n", encoding="utf-8")
        (self.project / "iteration-contract.json").write_text(json.dumps({
            "issue_id": "ISSUE-1", "pbs_leaf": "PBS-1", "story_refs": ["US-1"],
            "goal": "Implement the bounded behavior"
        }) + "\n", encoding="utf-8")
        (self.project / "iteration-budget.json").write_text(json.dumps({
            "producer": "trusted-iteration-budget-checker", "verdict": "PASS",
            "issue_id": "ISSUE-1", "pbs_leaf": "PBS-1"
        }) + "\n", encoding="utf-8")
        (self.project / "scaffold-integrity.json").write_text(json.dumps({
            "producer": "trusted-scaffold-integrity-checker", "verdict": "PASS",
            "issue_id": "ISSUE-1", "pbs_leaf": "PBS-1"
        }) + "\n", encoding="utf-8")
        self.write_critique(0.5)
        (iteration / "architect-checkpoint.json").write_text(json.dumps({
            "version": "1", "producer": "architect", "verdict": "CONTINUE",
            "model_id": "architect-model", "context_id": "architect-context", "review_ref": "architect.md",
            "checks": {"one_leaf": True, "boundaries_interfaces": True,
                       "requirements_delta": "none", "architecture_delta": "none",
                       "debt_delta": "none", "explanation_matches_evidence": True}
        }) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_critique(self, score: float) -> None:
        (self.project / ".build-loop" / "iterations" / "1" / "critique.json").write_text(json.dumps({
            "scores": {"c1": score}, "critique_per_criterion": {"c1": "checked"},
            "evidence_per_criterion": {"c1": ["evidence.log"]}
        }) + "\n", encoding="utf-8")

    def run_check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(CHECKER), "--project", str(self.project), "--iteration", "1", "--check-next"],
            text=True, capture_output=True, check=False,
        )

    def test_continue_requires_and_accepts_safe_architect_checkpoint(self) -> None:
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        dashboard = json.loads((self.project / ".build-loop" / "iterations" / "1" / "attempt-dashboard.json").read_text())
        self.assertEqual(dashboard["status"], "CONTINUE")
        self.assertEqual(dashboard["mechanical"]["budget_verdict"], "PASS")
        self.assertEqual(dashboard["architect"]["verdict"], "CONTINUE")
        markdown = (self.project / ".build-loop" / "iterations" / "1" / "dashboard.md").read_text()
        self.assertIn("```mermaid", markdown)
        self.assertIn("US-1", markdown)
        self.assertIn("PBS-1", markdown)
        self.assertIn("Architect checkpoint", markdown)
        self.assertIn("next bounded worker attempt", markdown)

    def test_pass_enters_terminal_review_and_never_starts_another_worker(self) -> None:
        self.write_critique(1.0)
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("terminal ordered review", result.stdout)
        markdown = (self.project / ".build-loop" / "iterations" / "1" / "dashboard.md").read_text()
        self.assertIn("```mermaid", markdown)
        self.assertIn("terminal ordered review", markdown)

    def test_material_delta_blocks_next_worker(self) -> None:
        path = self.project / ".build-loop" / "iterations" / "1" / "architect-checkpoint.json"
        checkpoint = json.loads(path.read_text())
        checkpoint["checks"]["requirements_delta"] = "material"
        path.write_text(json.dumps(checkpoint) + "\n", encoding="utf-8")
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirements authority", result.stdout)


if __name__ == "__main__":
    unittest.main()
