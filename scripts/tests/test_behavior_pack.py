#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "skills" / "visualization" / "scripts" / "check-behavior-pack.py"


class BehaviorPackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        behavior = self.project / "docs" / "behavior"
        (behavior / "interactions").mkdir(parents=True)
        (behavior / "flow-pay.md").write_text("# Flow\n", encoding="utf-8")
        (behavior / "uc-pay.md").write_text("# UC\n", encoding="utf-8")
        (behavior / "interactions" / "payment.md").write_text("# Interaction\n", encoding="utf-8")
        self.index = behavior / "behavior-index.json"
        self.data = {
            "version": "1",
            "flows": [{"id": "FLOW-PAY", "path": "docs/behavior/flow-pay.md", "use_case_ids": ["UC-PAY"], "criterion_refs": ["C1"]}],
            "use_cases": [{"id": "UC-PAY", "path": "docs/behavior/uc-pay.md", "flow_id": "FLOW-PAY", "steps": [{"number": 1, "text": "Submit payment"}], "contract_paths": ["contract.json#/user_flow/primary_path/0"], "critical": True}],
            "interactions": [{"id": "INT-PAY", "path": "docs/behavior/interactions/payment.md", "use_case_id": "UC-PAY", "step": 1, "question": "When is idempotency reserved?", "lifeline_count": 3, "node_count": 6, "max_nesting": 1, "split_justification": None}],
            "risk_probes": [],
            "coverage": {"uncovered_criteria": [], "uncovered_critical_error_paths": []}
        }
        self.write()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self) -> None:
        self.index.write_text(json.dumps(self.data) + "\n", encoding="utf-8")

    def check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["python3", str(CHECKER), "--project", str(self.project), "--root", str(ROOT)], text=True, capture_output=True, check=False)

    def test_valid_pack_passes(self) -> None:
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_critical_use_case_requires_contract_path(self) -> None:
        self.data["use_cases"][0]["contract_paths"] = []
        self.write()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("critical use case UC-PAY has no contract path", result.stdout)

    def test_over_budget_interaction_requires_split_justification(self) -> None:
        self.data["interactions"][0]["lifeline_count"] = 8
        self.write()
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPLIT_REQUIRED", result.stdout)


if __name__ == "__main__":
    unittest.main()
