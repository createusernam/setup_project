#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test trusted build-loop critique coverage and verdict computation.
# SCOPE: Execute verdict.sh against isolated contract, critique, and iteration-log fixtures.
# DEPENDS: Python unittest, Bash, and skills/build-loop/scripts/verdict.sh.
# END_MODULE_CONTRACT
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
VERDICT = ROOT / "skills" / "build-loop" / "scripts" / "verdict.sh"
CRITIQUE_SCHEMA = ROOT / "skills" / "build-loop" / "critique.schema.json"
SCHEMA_SPEC = importlib.util.spec_from_file_location("build_loop_json_schema", ROOT / "scripts" / "json_schema.py")
assert SCHEMA_SPEC and SCHEMA_SPEC.loader
schema_validator = importlib.util.module_from_spec(SCHEMA_SPEC)
SCHEMA_SPEC.loader.exec_module(schema_validator)


class BuildLoopVerdictTests(unittest.TestCase):
    def run_verdict(self, contract: dict, critique: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            iteration = project / ".build-loop" / "iterations" / "1"
            iteration.mkdir(parents=True)
            (project / "contract.json").write_text(json.dumps(contract) + "\n", encoding="utf-8")
            (iteration / "critique.json").write_text(critique, encoding="utf-8")
            (project / ".build-loop" / "iteration-log.json").write_text(
                json.dumps({"iterations": [], "restart_count": 0}) + "\n", encoding="utf-8"
            )
            return subprocess.run(
                ["bash", str(VERDICT), "1"],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_one_score_out_of_ten_cannot_pass(self) -> None:
        criteria = [
            {"id": f"C{index}", "weight": 1, "must_pass": index == 1}
            for index in range(1, 11)
        ]
        contract = {
            "criteria": criteria,
            "restart_threshold": {
                "max_iterations": 5,
                "no_progress_iterations": 3,
                "criteria_floor": 0.6,
            },
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 1.0},
                "critique_per_criterion": {"C1": "The observed behavior passed."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"]},
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "One observed criterion passed.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("missing criterion scores: C10, C2, C3, C4, C5, C6, C7, C8, C9", verdict["validation_errors"])

    def test_incomplete_critique_weighted_score_uses_full_contract_denominator(self) -> None:
        criteria = [{"id": f"C{index}", "weight": 1, "must_pass": False} for index in range(1, 11)]
        contract = {"criteria": criteria, "restart_threshold": {"criteria_floor": 0.6}}
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 1.0},
                "critique_per_criterion": {"C1": "Only one criterion observed."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"]},
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Overstates quality through omission.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertEqual(verdict["weighted_score"], 0.1)

    def test_duplicate_score_key_fails_closed(self) -> None:
        contract = {
            "criteria": [{"id": "C1", "weight": 1, "must_pass": True}],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = """{
          "iteration": 1,
          "scores": {"C1": 1.0, "C1": 0.0},
          "critique_per_criterion": {"C1": "Observed twice."},
          "evidence_per_criterion": {"C1": ["tests/C1.log"]},
          "verdict": "fail",
          "blocking_criteria": ["C1"],
          "summary": "Duplicate score key."
        }"""

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("duplicate JSON key in critique: C1", verdict["validation_errors"])

    def test_out_of_range_score_fails_closed(self) -> None:
        contract = {
            "criteria": [{"id": "C1", "weight": 1, "must_pass": True}],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 1.1},
                "critique_per_criterion": {"C1": "Claimed above the valid range."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"]},
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Invalid score.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("criterion C1 score must be a number from 0 to 1", verdict["validation_errors"])

    def test_every_criterion_requires_critique_and_evidence(self) -> None:
        contract = {
            "criteria": [
                {"id": "C1", "weight": 1, "must_pass": True},
                {"id": "C2", "weight": 1, "must_pass": False},
            ],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 1.0, "C2": 1.0},
                "critique_per_criterion": {"C2": "Observed C2."},
                "evidence_per_criterion": {"C2": ["tests/C2.log"]},
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "C1 lacks evaluation support.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("missing criterion critiques: C1", verdict["validation_errors"])
        self.assertIn("missing criterion evidence: C1", verdict["validation_errors"])

    def test_criteria_floor_applies_to_each_criterion(self) -> None:
        contract = {
            "criteria": [
                {"id": "C1", "weight": 0.001, "must_pass": False},
                {"id": "C2", "weight": 1, "must_pass": False},
            ],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 0.0, "C2": 1.0},
                "critique_per_criterion": {"C1": "C1 failed.", "C2": "C2 passed."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"], "C2": ["tests/C2.log"]},
                "weighted_score": 1.0,
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Aggregate hides C1.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertEqual(verdict["criteria_floor_failures"], ["C1"])
        self.assertLess(verdict["weighted_score"], 1.0)

    def test_committed_critique_schema_rejects_out_of_range_score(self) -> None:
        schema = json.loads(CRITIQUE_SCHEMA.read_text(encoding="utf-8"))
        document = json.loads(
            (ROOT / "skills" / "build-loop" / "templates" / "critique.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema_validator.validate(document, schema), [])

        document["scores"]["c1"] = 2

        self.assertTrue(schema_validator.validate(document, schema))

    def test_duplicate_contract_criterion_id_fails_closed(self) -> None:
        contract = {
            "criteria": [
                {"id": "C1", "weight": 1, "must_pass": False},
                {"id": "C1", "weight": 1, "must_pass": False},
            ],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 1.0},
                "critique_per_criterion": {"C1": "Observed once."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"]},
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Duplicate contract ID.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("duplicate contract criterion id: C1", verdict["validation_errors"])

    def test_scores_must_be_an_object(self) -> None:
        contract = {
            "criteria": [{"id": "C1", "weight": 1, "must_pass": True}],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": ["C1"],
                "critique_per_criterion": {"C1": "Observed."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"]},
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Malformed scores.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("scores must be an object", verdict["validation_errors"])

    def test_unknown_score_id_fails_closed(self) -> None:
        contract = {
            "criteria": [{"id": "C1", "weight": 1, "must_pass": True}],
            "restart_threshold": {"criteria_floor": 0.6},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 1.0, "UNKNOWN": 1.0},
                "critique_per_criterion": {"C1": "Observed.", "UNKNOWN": "Not contracted."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"], "UNKNOWN": ["tests/unknown.log"]},
                "weighted_score": 1.0,
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Unknown criterion included.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["verdict"], "fail")
        self.assertIn("unknown criterion scores: UNKNOWN", verdict["validation_errors"])

    def test_evaluator_weighted_score_is_not_trusted(self) -> None:
        contract = {
            "criteria": [{"id": "C1", "weight": 1, "must_pass": False}],
            "restart_threshold": {"criteria_floor": 0.4},
        }
        critique = json.dumps(
            {
                "iteration": 1,
                "scores": {"C1": 0.5},
                "critique_per_criterion": {"C1": "Partially observed."},
                "evidence_per_criterion": {"C1": ["tests/C1.log"]},
                "weighted_score": 1.0,
                "verdict": "pass",
                "blocking_criteria": [],
                "summary": "Evaluator claims a perfect aggregate.",
            }
        )

        result = self.run_verdict(contract, critique)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["weighted_score"], 0.5)
        self.assertNotEqual(verdict["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
