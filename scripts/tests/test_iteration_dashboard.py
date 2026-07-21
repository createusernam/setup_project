#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test canonical iteration dashboards in the existing viewpoint and SUPERVISION flow.
# SCOPE: Cover five statuses, trusted metrics, deterministic Markdown tables, viewpoint metadata, and supervision links.
# DEPENDS: Python unittest, visualization renderer, and dashboard/viewpoint schemas.
# END_MODULE_CONTRACT
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "skills" / "visualization" / "scripts" / "render-iteration-dashboard.py"


class IterationDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        (self.project / "SUPERVISION.md").write_text(
            "# Supervision\n\n- [Current iteration dashboard](dashboard.md)\n", encoding="utf-8"
        )
        self.write("iteration-contract.json", {
            "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "goal": "Implement one bounded leaf.",
            "story_refs": ["US-1"],
            "criterion_refs": ["C1", "C2"], "verify_commands": ["pytest"],
            "models": {"worker": "model/worker", "architect": "model/architect", "test_owner": "model/test", "acceptor": "model/acceptor"},
        })
        self.write("contract.json", {"criteria": [{"id": "C1", "must_pass": True}, {"id": "C2", "must_pass": False}]})
        self.write("iteration-budget.json", {
            "verdict": "PASS", "baseline_commit": "a" * 40,
            "budget": {
                "production_loc": {"actual": 20, "target": 200, "max": 400, "target_exceeded": False, "hard_max_exceeded": False},
                "total_loc": {"actual": 45, "target": 400, "max": 800, "target_exceeded": False, "hard_max_exceeded": False},
                "files": {"actual": 3, "target": 6, "max": 10, "target_exceeded": False, "hard_max_exceeded": False},
                "public_interfaces": {"actual": 1, "target": 1, "max": 2, "target_exceeded": False, "hard_max_exceeded": False},
            }, "changed_files": [{"path": "src/leaf.py"}], "scope_breaches": [], "split_reasons": [],
        })
        self.write("scaffold-integrity.json", {"verdict": "PASS", "violations": [], "gap": None})
        self.write("iteration-review.json", {
            "architect": {"model_id": "model/architect", "verdict": "PASS"},
            "worker": {"model_id": "model/worker"}, "test_owner": {"model_id": "model/test", "verdict": "PASS"},
            "acceptor": {"model_id": "model/acceptor", "verdict": "PASS"}, "mechanical": {"verdict": "PASS"},
        })
        self.write("build-evidence.json", {
            "status": "complete", "criteria": [{"id": "C1", "status": "PASS", "evidence_ref": "traces/c1.log"}, {"id": "C2", "status": "PASS", "evidence_ref": "screenshots/c2.png"}],
            "checks": [{"command": "pytest", "status": "pass", "evidence_ref": "tests.log"}],
            "trace_refs": ["traces/c1.log"], "requirements_delta": {"status": "none", "items": []},
            "debt_delta": {"status": "none", "items": []},
            "scaffold_integrity": {"status": "unchanged", "report_ref": "scaffold-integrity.json", "architect_review_ref": None},
            "residual_risks": [],
        })

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, name: str, value: dict) -> None:
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    def render(self) -> tuple[subprocess.CompletedProcess[str], dict, str]:
        result = subprocess.run(
            ["python3", str(RENDERER), "--project", str(self.project)], text=True, capture_output=True, check=False
        )
        dashboard_path = self.project / "iteration-dashboard.json"
        markdown_path = self.project / "iterations" / "ISSUE-1" / "dashboard.md"
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8")) if dashboard_path.is_file() else {}
        markdown = markdown_path.read_text(encoding="utf-8") if markdown_path.is_file() else ""
        return result, dashboard, markdown

    def test_pass_dashboard_uses_tables_and_trusted_artifacts(self) -> None:
        result, dashboard, markdown = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(dashboard["status"], "PASS")
        self.assertEqual(dashboard["pbs_leaf"], "PBS-LEAF-1")
        self.assertEqual(dashboard["criteria"]["coverage"], "2/2")
        self.assertEqual(dashboard["criteria"]["must_pass"], "1/1")
        self.assertEqual(dashboard["models"]["worker"], "model/worker")
        self.assertIn("| Metric | Actual | Target | Hard max |", markdown)
        self.assertNotIn("```mermaid", markdown)

    def test_all_five_dashboard_states_have_legal_next_action(self) -> None:
        cases = [
            ("PASS", None),
            ("REVISE", ("iteration-review.json", "architect", "verdict", "REVISE")),
            ("SPLIT_REQUIRED", ("iteration-budget.json", None, "verdict", "SPLIT_REQUIRED")),
            ("CONTRACT_GAP", ("scaffold-integrity.json", None, "verdict", "CONTRACT_GAP")),
            ("RESTART", ("iteration-review.json", "acceptor", "verdict", "RESTART")),
        ]
        originals = {name: json.loads((self.project / name).read_text()) for name in ("iteration-budget.json", "scaffold-integrity.json", "iteration-review.json")}
        for expected, mutation in cases:
            with self.subTest(expected=expected):
                for name, value in originals.items():
                    self.write(name, value)
                if mutation:
                    name, section, key, value = mutation
                    document = json.loads((self.project / name).read_text())
                    target = document[section] if section else document
                    target[key] = value
                    self.write(name, document)
                result, dashboard, _ = self.render()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(dashboard["status"], expected)
                self.assertTrue(dashboard["legal_next_action"])

    def test_renderer_is_deterministic_and_updates_supervision_and_viewpoint(self) -> None:
        first, dashboard, _ = self.render()
        first_json = (self.project / "iteration-dashboard.json").read_bytes()
        first_md = (self.project / "iterations" / "ISSUE-1" / "dashboard.md").read_bytes()
        second, second_dashboard, _ = self.render()
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(dashboard, second_dashboard)
        self.assertEqual(first_json, (self.project / "iteration-dashboard.json").read_bytes())
        self.assertEqual(first_md, (self.project / "iterations" / "ISSUE-1" / "dashboard.md").read_bytes())
        supervision = (self.project / "SUPERVISION.md").read_text(encoding="utf-8")
        self.assertIn("[Current iteration dashboard](dashboard.md)", supervision)
        self.assertEqual(
            (self.project / "dashboard.md").read_bytes(),
            (self.project / "iterations" / "ISSUE-1" / "dashboard.md").read_bytes(),
        )
        viewpoint = json.loads((self.project / "docs" / "views" / "iteration-issue-1.json").read_text())
        self.assertEqual(viewpoint["concern"], "dynamics")
        self.assertEqual(viewpoint["scale"], "operation")
        self.assertIn("iteration-dashboard.json", viewpoint["canonical_refs"])
        check = subprocess.run(
            ["python3", str(RENDERER), "--project", str(self.project), "--check"],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_dashboard_declares_schema_producer_and_consumers(self) -> None:
        result, dashboard, _ = self.render()
        self.assertEqual(result.returncode, 0)
        self.assertTrue((ROOT / "templates" / "project" / "iteration-dashboard.schema.json").is_file())
        self.assertEqual(dashboard["producer"], "trusted-iteration-dashboard-renderer")
        self.assertEqual(dashboard["consumers"], ["human-supervision", "phase6-semantic-validator"])
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        self.assertEqual(machine["artifact_owners"]["iteration-dashboard.json"]["producer_phase"], "6")
        self.assertIn(
            {"artifact": "iteration-dashboard.json", "attested": True, "json_pointer": "/status", "equals": "PASS", "tiers": ["T2", "T3", "T4"]},
            machine["transitions"]["7"]["requires"],
        )
        self.assertIn("iteration-dashboard.json", machine["invalidations"]["build-evidence.json"])

    def test_unlisted_required_verify_command_downgrades_pass(self) -> None:
        iteration = json.loads((self.project / "iteration-contract.json").read_text(encoding="utf-8"))
        iteration["verify_commands"] = ["pytest", "typecheck"]
        self.write("iteration-contract.json", iteration)

        result, dashboard, _ = self.render()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(dashboard["status"], "REVISE")

    def test_latest_critique_link_uses_numeric_iteration_order(self) -> None:
        for iteration_number in (2, 10):
            path = self.project / ".build-loop" / "iterations" / str(iteration_number) / "critique.json"
            path.parent.mkdir(parents=True)
            path.write_text("{}\n", encoding="utf-8")

        result, dashboard, _ = self.render()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(dashboard["links"]["critique"], ".build-loop/iterations/10/critique.json")

    def test_incomplete_evidence_cannot_render_pass(self) -> None:
        evidence = json.loads((self.project / "build-evidence.json").read_text())
        evidence["status"] = "incomplete"
        self.write("build-evidence.json", evidence)
        result, dashboard, _ = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(dashboard["status"], "REVISE")

    def test_architect_approved_scaffold_drift_can_render_pass(self) -> None:
        integrity = json.loads((self.project / "scaffold-integrity.json").read_text())
        integrity["verdict"] = "SCAFFOLD_DRIFT"
        integrity["violations"] = [{"type": "contract_anchor_drift"}]
        self.write("scaffold-integrity.json", integrity)
        evidence = json.loads((self.project / "build-evidence.json").read_text())
        evidence["scaffold_integrity"] = {
            "status": "architect_approved", "report_ref": "scaffold-integrity.json",
            "architect_review_ref": "reviews/architect.md",
        }
        self.write("build-evidence.json", evidence)
        result, dashboard, _ = self.render()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(dashboard["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
