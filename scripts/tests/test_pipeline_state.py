#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test human pipeline ledger initialization, attestation, invalidation, and signing.
# SCOPE: Exercise pipeline-state.py against a temporary project without external dependencies.
# DEPENDS: Python standard library and scripts/pipeline-state.py.
# END_MODULE_CONTRACT
from __future__ import annotations

import importlib.util
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


class PipelineStateTests(unittest.TestCase):
    def test_attest_change_invalidates_consumers_and_signs_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            (project / "product_brief.md").write_text("v1\n", encoding="utf-8")
            (project / "task_plan.md").write_text("plan\n", encoding="utf-8")

            module.command_attest(SimpleNamespace(artifacts=["product_brief.md", "task_plan.md"], status="ready"), ROOT, project)
            ledger_path = project / ".pipeline-state.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["status"], "ready")

            (project / "product_brief.md").write_text("v2\n", encoding="utf-8")
            module.command_attest(SimpleNamespace(artifacts=["product_brief.md"], status="approved"), ROOT, project)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["status"], "invalidated")
            self.assertEqual(ledger["artifacts"]["task_plan.md"]["invalidated_by"], "product_brief.md")

            module.command_sign(SimpleNamespace(gate="contract_locked", by="owner@example.test"), ROOT, project)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["human_gates"]["contract_locked"]["by"], "owner@example.test")

    def test_rejects_artifact_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            module.command_init(SimpleNamespace(force=False), ROOT, project)
            with self.assertRaisesRegex(ValueError, "inside the project"):
                module.command_attest(SimpleNamespace(artifacts=["../outside"], status="ready"), ROOT, project)


if __name__ == "__main__":
    unittest.main()
