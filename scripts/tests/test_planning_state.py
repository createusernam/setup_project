#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Protect the v2 planning-state schema and validate-before-render persistence boundary.
# SCOPE: Test valid initialization, malformed element shapes, statuses, current phase, and view stability.
# DEPENDS: Python unittest, standard library, and planning-state.py.
# END_MODULE_CONTRACT
"""Regression tests for JSON-canonical planning state."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills" / "planning-with-files" / "scripts" / "planning-state.py"


class PlanningStateTests(unittest.TestCase):
    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *arguments], text=True, capture_output=True, check=False)

    def test_initializer_produces_schema_valid_v2_and_rendered_views(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.command("init", str(root), "--created", "2026-07-22")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((root / "task_plan.json").read_text())["version"], "2")
            self.assertTrue((root / "task_plan.md").read_text().startswith("<!-- GENERATED"))

    def test_invalid_state_reports_paths_and_preserves_all_views(self) -> None:
        mutations = {
            "string task": lambda plan: plan["phases"][0]["tasks"].append("not an object"),
            "string decision": lambda plan: plan["decisions"].append("not an object"),
            "string error": lambda plan: plan["errors"].append("not an object"),
            "unknown status": lambda plan: plan["phases"][0].update(status="running"),
            "mismatched current phase": lambda plan: plan.update(current_phase=2),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                initialized = self.command("init", str(root), "--created", "2026-07-22")
                self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
                before = {name: (root / name).read_bytes() for name in ("task_plan.md", "findings.md", "progress.md")}
                plan_path = root / "task_plan.json"
                plan = json.loads(plan_path.read_text())
                mutate(plan)
                plan_path.write_text(json.dumps(plan), encoding="utf-8")

                result = self.command("render", str(root))

                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("task_plan.json:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual({name: (root / name).read_bytes() for name in before}, before)


if __name__ == "__main__":
    unittest.main()
