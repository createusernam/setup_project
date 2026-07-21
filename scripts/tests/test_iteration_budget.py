#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test trusted Phase 6 diff scope and budget classification.
# SCOPE: Exercise PASS, SPLIT_REQUIRED, SCOPE_BREACH, category metrics, and canonical JSON output.
# DEPENDS: Python unittest, git, iteration contract template, and build-loop budget checker.
# END_MODULE_CONTRACT
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "skills" / "build-loop" / "scripts" / "check-iteration-budget.py"
SCHEMA = ROOT / "templates" / "project" / "iteration-budget.schema.json"


class IterationBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "tests@example.invalid")
        self.run_git("config", "user.name", "Budget Tests")
        (self.project / "src").mkdir()
        (self.project / "tests").mkdir()
        (self.project / "docs").mkdir()
        (self.project / "src" / "leaf.py").write_text("# PBS_LEAF: PBS-LEAF-1\nvalue = 1\n", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "baseline")
        self.baseline = self.run_git("rev-parse", "HEAD").stdout.strip()
        self.write_contract()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.project, text=True, capture_output=True, check=True
        )

    def write_contract(self, **overrides: object) -> None:
        contract = {
            "version": "1",
            "status": "ready",
            "issue_id": "ISSUE-1",
            "pbs_leaf": "PBS-LEAF-1",
            "baseline_commit": self.baseline,
            "allowed_paths": ["src/**", "tests/**", "docs/**"],
            "forbidden_paths": ["src/secrets/**"],
            "production_loc_target": 200,
            "production_loc_max": 400,
            "total_loc_target": 400,
            "total_loc_max": 800,
            "files_target": 6,
            "max_files": 10,
            "public_interfaces_target": 1,
            "max_public_interfaces": 2,
        }
        contract.update(overrides)
        (self.project / "iteration-contract.json").write_text(
            json.dumps(contract) + "\n", encoding="utf-8"
        )
        self.run_git("add", "iteration-contract.json")
        self.run_git("commit", "-qm", "iteration contract", "--allow-empty")

    def check(self) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            ["python3", str(CHECKER), "--project", str(self.project)],
            text=True,
            capture_output=True,
            check=False,
        )
        output = self.project / "iteration-budget.json"
        document = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else {}
        return result, document

    def test_bounded_one_leaf_diff_passes_and_classifies_all_buckets(self) -> None:
        (self.project / "src" / "leaf.py").write_text(
            "# PBS_LEAF: PBS-LEAF-1\ndef bounded_api():\n    return 2\n", encoding="utf-8"
        )
        (self.project / "tests" / "test_leaf.py").write_text("assert True\n", encoding="utf-8")
        (self.project / "docs" / "leaf.md").write_text("Leaf notes.\n", encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(document["verdict"], "PASS")
        self.assertEqual(document["pbs_leaf"], "PBS-LEAF-1")
        self.assertEqual(document["metrics"]["production"]["files"], 1)
        self.assertEqual(document["metrics"]["tests"]["files"], 1)
        self.assertEqual(document["metrics"]["docs"]["files"], 1)
        self.assertEqual(document["budget"]["public_interfaces"]["actual"], 1)

    def test_test_and_doc_definitions_do_not_consume_interface_budget(self) -> None:
        (self.project / "src" / "leaf.py").write_text("def bounded_api():\n    return 2\n", encoding="utf-8")
        (self.project / "tests" / "test_leaf.py").write_text(
            "class LeafTests:\n    def test_one(self):\n        assert True\n\n"
            "    def test_two(self):\n        assert True\n",
            encoding="utf-8",
        )
        (self.project / "docs" / "leaf.md").write_text(
            "```python\ndef example():\n    pass\n```\n", encoding="utf-8"
        )

        result, document = self.check()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(document["verdict"], "PASS")
        self.assertEqual(document["budget"]["public_interfaces"]["actual"], 1)

    def test_more_than_800_source_loc_is_split_required(self) -> None:
        (self.project / "tests" / "large.py").write_text("assert True\n" * 801, encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(document["verdict"], "SPLIT_REQUIRED")
        self.assertGreater(document["budget"]["total_loc"]["actual"], 800)
        self.assertIn("total_loc_max", document["split_reasons"])

    def test_more_than_one_changed_leaf_marker_is_split_required(self) -> None:
        (self.project / "src" / "leaf.py").write_text(
            "# PBS_LEAF: PBS-LEAF-1\n# PBS_LEAF: PBS-LEAF-2\nvalue = 2\n", encoding="utf-8"
        )

        result, document = self.check()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(document["verdict"], "SPLIT_REQUIRED")
        self.assertEqual(document["observed_pbs_leaves"], ["PBS-LEAF-1", "PBS-LEAF-2"])
        self.assertIn("multiple_pbs_leaves", document["split_reasons"])

    def test_forbidden_path_is_scope_breach_even_when_oversized(self) -> None:
        path = self.project / "src" / "secrets" / "dump.py"
        path.parent.mkdir()
        path.write_text("secret = 1\n" * 900, encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 3)
        self.assertEqual(document["verdict"], "SCOPE_BREACH")
        self.assertIn("src/secrets/dump.py", document["scope_breaches"])
        self.assertIn("total_loc_max", document["split_reasons"])

    def test_path_outside_allowlist_is_scope_breach(self) -> None:
        (self.project / "config.yml").write_text("unsafe: true\n", encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 3)
        self.assertEqual(document["verdict"], "SCOPE_BREACH")
        self.assertIn("config.yml", document["scope_breaches"])

    def test_generated_vendor_and_lock_loc_are_reported_but_do_not_hide_source(self) -> None:
        self.write_contract(allowed_paths=["src/**", "docs/views/**", "vendor/**", "*.lock"])
        (self.project / "src" / "leaf.py").write_text("x = 1\n" * 401, encoding="utf-8")
        generated = self.project / "docs" / "views" / "phase.json"
        generated.parent.mkdir(parents=True)
        generated.write_text("{}\n" * 500, encoding="utf-8")
        vendor = self.project / "vendor" / "lib.js"
        vendor.parent.mkdir()
        vendor.write_text("x\n" * 500, encoding="utf-8")
        (self.project / "deps.lock").write_text("locked\n" * 500, encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(document["verdict"], "SPLIT_REQUIRED")
        self.assertGreater(document["metrics"]["generated"]["changed_loc"], 0)
        self.assertGreater(document["metrics"]["vendor"]["changed_loc"], 0)
        self.assertGreater(document["metrics"]["lock"]["changed_loc"], 0)
        self.assertGreater(document["budget"]["production_loc"]["actual"], 400)

    def test_orchestrator_state_is_not_measured_as_worker_scope(self) -> None:
        (self.project / "src" / "leaf.py").write_text("value = 2\n", encoding="utf-8")
        state = self.project / ".build-loop" / "iterations" / "1"
        state.mkdir(parents=True)
        (state / "critique.json").write_text("{}\n", encoding="utf-8")
        (self.project / ".build-loop" / "iteration-log.json").write_text("{}\n", encoding="utf-8")
        for artifact in ("build-evidence.json", "iteration-review.json", "scaffold-integrity.json", "iteration-dashboard.json"):
            (self.project / artifact).write_text("{}\n", encoding="utf-8")
        (self.project / "dashboard.md").write_text("# Dashboard\n", encoding="utf-8")
        archive = self.project / "iterations" / "ISSUE-1"
        archive.mkdir(parents=True)
        (archive / "dashboard.md").write_text("# Dashboard\n", encoding="utf-8")
        views = self.project / "docs" / "views"
        views.mkdir(parents=True)
        (views / "iteration-issue-1.json").write_text("{}\n", encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(document["verdict"], "PASS")
        measured = {item["path"] for item in document["changed_files"]}
        self.assertEqual(measured, {"src/leaf.py"})

    def test_worktree_iteration_contract_differing_from_head_is_rejected(self) -> None:
        tampered = json.loads((self.project / "iteration-contract.json").read_text(encoding="utf-8"))
        tampered["production_loc_max"] = 100000
        tampered["allowed_paths"] = ["**"]
        (self.project / "iteration-contract.json").write_text(json.dumps(tampered) + "\n", encoding="utf-8")

        result, document = self.check()

        self.assertEqual(result.returncode, 1)
        self.assertIn("committed", result.stdout)
        self.assertEqual(document, {})

    def test_output_has_schema_producer_consumer_and_deterministic_bytes(self) -> None:
        (self.project / "src" / "leaf.py").write_text("value = 2\n", encoding="utf-8")
        first, first_document = self.check()
        first_bytes = (self.project / "iteration-budget.json").read_bytes()
        second, second_document = self.check()

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(first_document, second_document)
        self.assertEqual(first_bytes, (self.project / "iteration-budget.json").read_bytes())
        self.assertTrue(SCHEMA.is_file())
        self.assertEqual(first_document["producer"], "trusted-iteration-budget-checker")
        self.assertIn("phase6-semantic-validator", first_document["consumers"])


if __name__ == "__main__":
    unittest.main()
