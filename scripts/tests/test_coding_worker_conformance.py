#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test role-specific coding-worker conformance and critical probe qualification.
# SCOPE: Ensure exact critical coverage cannot be masked by aggregate pass rate and preflight enforces the profile.
# DEPENDS: Python unittest, conformance schema, provider-neutral harness, and pipeline preflight.
# END_MODULE_CONTRACT
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CRITICAL = {
    "bounded_patch", "allowed_path_compliance", "compiler_typecheck_feedback",
    "targeted_test_execution", "scaffold_anchor_preservation", "stop_on_contract_gap",
    "secret_non_disclosure", "destructive_command_refusal",
    "untrusted_repository_instruction_resistance", "schema_valid_handoff_dashboard_input",
    "failure_recovery",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


schema_validator = load("coding_schema", ROOT / "scripts" / "json_schema.py")
preflight = load("coding_preflight", ROOT / "scripts" / "pipeline_preflight.py")
harness = load("coding_harness", ROOT / "scripts" / "model-conformance.py")


def document(*, failed: str | None = None, omit: str | None = None) -> dict:
    scenarios = [
        {"id": probe, "critical": True, "status": "fail" if probe == failed else "pass", "attempts": 1, "latency_ms": 0, "evidence": {}}
        for probe in sorted(CRITICAL - ({omit} if omit else set()))
    ]
    scenarios += [
        {"id": f"general-{index}", "critical": False, "status": "pass", "attempts": 1, "latency_ms": 0, "evidence": {}}
        for index in range(40)
    ]
    summary = harness.qualification(scenarios, 0.8, "coding_worker")
    return {
        "$schema": "../model-conformance.schema.json", "version": "1", "harness_version": "2",
        "profile": "coding_worker", "provider": "fixture", "runtime": "api", "model_id": "fixture/code",
        "endpoint_host": "example.test", "executed_at": "2026-07-21T00:00:00Z",
        "settings": {"temperature": 0, "max_tokens": 1, "timeout_seconds": 1, "max_repair_attempts": 0, "thinking": "disabled"},
        "scenarios": scenarios, "summary": summary,
        "provenance": {"setup_git_sha": "fixture", "runner_sha256": "0" * 64},
    }


class CodingWorkerConformanceTests(unittest.TestCase):
    def test_all_critical_coding_probes_are_schema_valid_and_qualify(self) -> None:
        evidence = document()
        schema = json.loads((ROOT / "templates/project/model-conformance.schema.json").read_text())
        self.assertEqual(schema_validator.validate(evidence, schema), [])
        self.assertTrue(evidence["summary"]["qualified"])
        self.assertEqual(evidence["summary"]["critical_failures"], [])

    def test_one_critical_failure_cannot_be_hidden_by_high_pass_rate(self) -> None:
        evidence = document(failed="destructive_command_refusal")
        self.assertGreater(evidence["summary"]["pass_rate"], 0.8)
        self.assertFalse(evidence["summary"]["qualified"])
        self.assertEqual(evidence["summary"]["critical_failures"], ["destructive_command_refusal"])

    def test_missing_critical_probe_fails_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            path = project / "model-conformance" / "code.json"
            path.parent.mkdir()
            path.write_text(json.dumps(document(omit="secret_non_disclosure")) + "\n", encoding="utf-8")
            binding = {"enabled": True, "model_id": "fixture/code", "conformance_ref": "model-conformance/code.json"}
            policy = {"mode": "required", "minimum_pass_rate": 0.8, "harness_version": "2"}
            machine = json.loads((ROOT / "pipeline-machine.json").read_text())
            failures = preflight.model_conformance_errors(ROOT, project, machine, "implementation_general", binding, policy)
        self.assertTrue(any("critical coding probes" in failure for failure in failures), failures)

    def test_general_profile_cannot_qualify_implementation_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            evidence = document()
            evidence["profile"] = "general"
            path = project / "model-conformance" / "code.json"
            path.parent.mkdir()
            path.write_text(json.dumps(evidence) + "\n", encoding="utf-8")
            binding = {"enabled": True, "model_id": "fixture/code", "conformance_ref": "model-conformance/code.json"}
            policy = {"mode": "required", "minimum_pass_rate": 0.8, "harness_version": "2"}
            machine = json.loads((ROOT / "pipeline-machine.json").read_text())
            failures = preflight.model_conformance_errors(ROOT, project, machine, "implementation_general", binding, policy)
        self.assertTrue(any("coding_worker profile" in failure for failure in failures), failures)


if __name__ == "__main__":
    unittest.main()
