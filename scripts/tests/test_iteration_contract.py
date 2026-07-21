#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test the canonical one-leaf iteration contract and its trusted validator.
# SCOPE: Validate schema defaults, upstream lineage, model identity, and one-issue/PBS semantics.
# DEPENDS: Python unittest, portable JSON Schema validator, and scaffold iteration validator.
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
SCHEMA_PATH = ROOT / "templates" / "project" / "iteration-contract.schema.json"
VALIDATOR = ROOT / "skills" / "scaffold" / "scripts" / "validate-iteration-contract.py"
SCHEMA_SPEC = importlib.util.spec_from_file_location("iteration_json_schema", ROOT / "scripts" / "json_schema.py")
assert SCHEMA_SPEC and SCHEMA_SPEC.loader
schema_validator = importlib.util.module_from_spec(SCHEMA_SPEC)
SCHEMA_SPEC.loader.exec_module(schema_validator)


def valid_iteration_contract() -> dict:
    return {
        "$schema": "./iteration-contract.schema.json",
        "version": "1",
        "status": "ready",
        "issue_id": "ISSUE-1",
        "pbs_leaf": "PBS-LEAF-1",
        "goal": "Implement one bounded behavior.",
        "story_refs": ["US-1"],
        "criterion_refs": ["C1"],
        "contract_sha256": "1" * 64,
        "issues_manifest_sha256": "2" * 64,
        "scaffold_manifest_sha256": "3" * 64,
        "baseline_commit": "4" * 40,
        "allowed_paths": ["src/**", "tests/**"],
        "forbidden_paths": ["secrets/**"],
        "allowed_commands": ["python3 -m unittest tests.test_leaf"],
        "network_policy": {"mode": "deny", "allowed_hosts": []},
        "production_loc_target": 200,
        "production_loc_max": 400,
        "total_loc_target": 400,
        "total_loc_max": 800,
        "files_target": 6,
        "max_files": 10,
        "public_interfaces_target": 1,
        "max_public_interfaces": 2,
        "scaffold_files": ["src/leaf.py"],
        "contract_anchor_hashes": {"src/leaf.py#MODULE_CONTRACT": "5" * 64},
        "verify_commands": ["python3 -m unittest tests.test_leaf"],
        "required_trace_refs": ["TRACE-1"],
        "requirement_delta_policy": "fail_closed",
        "debt_delta_policy": "zero_or_owner_accepted",
        "models": {
            "architect": "provider/architect",
            "worker": "provider/worker",
            "test_owner": "provider/test-owner",
            "acceptor": "provider/acceptor"
        }
    }


class IterationContractTests(unittest.TestCase):
    def run_validator(self, iteration: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            documents = {
                "contract.json": {"criteria": [{"id": "C1"}]},
                "issues-manifest.json": {
                    "status": "approved",
                    "issues": [{"id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "story_refs": ["US-1"], "technical_enabler_for": [], "criterion_refs": ["C1"]}],
                },
                "scaffold-manifest.json": {
                    "status": "ready", "issue_id": "ISSUE-1",
                    "files": [{"path": "src/leaf.py", "pbs_leaf": "PBS-LEAF-1"}],
                },
                "model-bindings.json": {
                    "bindings": {
                        "reasoning_high": {"enabled": True, "model_id": "provider/architect"},
                        "implementation_general": {"enabled": True, "model_id": "provider/worker"},
                        "review_test": {"enabled": True, "model_id": "provider/test-owner"},
                        "review_acceptance": {"enabled": True, "model_id": "provider/acceptor"},
                    }
                },
            }
            for name, document in documents.items():
                (project / name).write_text(json.dumps(document) + "\n", encoding="utf-8")
            iteration["contract_sha256"] = hashlib.sha256((project / "contract.json").read_bytes()).hexdigest()
            iteration["issues_manifest_sha256"] = hashlib.sha256((project / "issues-manifest.json").read_bytes()).hexdigest()
            iteration["scaffold_manifest_sha256"] = hashlib.sha256((project / "scaffold-manifest.json").read_bytes()).hexdigest()
            (project / "iteration-contract.json").write_text(json.dumps(iteration) + "\n", encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)], text=True, capture_output=True, check=False
            )

    def test_schema_accepts_the_bounded_default_contract(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        document = valid_iteration_contract()

        self.assertEqual(schema_validator.validate(document, schema), [])

        document["total_loc_max"] = 801

        self.assertTrue(schema_validator.validate(document, schema))

    def test_validator_rejects_pbs_leaf_mismatch_across_issue_and_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            contract = {"criteria": [{"id": "C1"}]}
            issues = {
                "status": "approved",
                "issues": [{"id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "story_refs": ["US-1"], "technical_enabler_for": [], "criterion_refs": ["C1"]}],
            }
            scaffold = {
                "status": "ready",
                "issue_id": "ISSUE-1",
                "files": [{"path": "src/leaf.py", "pbs_leaf": "PBS-LEAF-1"}],
            }
            bindings = {
                "bindings": {
                    "reasoning_high": {"enabled": True, "model_id": "provider/architect"},
                    "implementation_general": {"enabled": True, "model_id": "provider/worker"},
                    "review_test": {"enabled": True, "model_id": "provider/test-owner"},
                    "review_acceptance": {"enabled": True, "model_id": "provider/acceptor"},
                }
            }
            documents = {
                "contract.json": contract,
                "issues-manifest.json": issues,
                "scaffold-manifest.json": scaffold,
                "model-bindings.json": bindings,
            }
            for name, document in documents.items():
                (project / name).write_text(json.dumps(document) + "\n", encoding="utf-8")
            iteration = valid_iteration_contract()
            iteration["pbs_leaf"] = "PBS-LEAF-2"
            iteration["contract_sha256"] = hashlib.sha256((project / "contract.json").read_bytes()).hexdigest()
            iteration["issues_manifest_sha256"] = hashlib.sha256((project / "issues-manifest.json").read_bytes()).hexdigest()
            iteration["scaffold_manifest_sha256"] = hashlib.sha256((project / "scaffold-manifest.json").read_bytes()).hexdigest()
            (project / "iteration-contract.json").write_text(json.dumps(iteration) + "\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pbs_leaf does not match approved issue", result.stdout)
        self.assertIn("pbs_leaf does not match scaffold files", result.stdout)

    def test_upstream_manifest_schemas_carry_leaf_lineage(self) -> None:
        issues_schema = json.loads(
            (ROOT / "templates" / "project" / "issues-manifest.schema.json").read_text(encoding="utf-8")
        )
        scaffold_schema = json.loads(
            (ROOT / "templates" / "project" / "scaffold-manifest.schema.json").read_text(encoding="utf-8")
        )
        issues = {
            "$schema": "./issues-manifest.schema.json",
            "version": "1",
            "status": "approved",
            "plan_ref": "task_plan.md",
            "contract_ref": "contract.json",
            "issues": [{
                "id": "ISSUE-1", "title": "One leaf", "type": "AFK", "pbs_leaf": "PBS-LEAF-1",
                "blocked_by": [], "story_refs": ["US-1"], "technical_enabler_for": [], "criterion_refs": ["C1"]
            }],
        }
        scaffold = {
            "$schema": "./scaffold-manifest.schema.json",
            "version": "1",
            "status": "ready",
            "issue_id": "ISSUE-1",
            "contract_sha256": "1" * 64,
            "files": [{"path": "src/leaf.py", "module_id": "M1", "pbs_leaf": "PBS-LEAF-1", "block_count": 1}],
            "checks": [{"command": "typecheck", "status": "pass"}],
        }

        self.assertEqual(schema_validator.validate(issues, issues_schema), [])
        self.assertEqual(schema_validator.validate(scaffold, scaffold_schema), [])

    def test_machine_registers_iteration_contract_from_scaffold_to_phase6(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))

        self.assertEqual(machine["artifact_owners"]["iteration-contract.json"]["producer_phase"], "5.5")
        self.assertIn(
            {"artifact": "iteration-contract.json", "attested": True, "json_pointer": "/status", "equals": "ready"},
            machine["transitions"]["6"]["requires"],
        )
        self.assertIn("build-evidence.json", machine["invalidations"]["iteration-contract.json"])

    def test_validator_rejects_model_binding_mismatch_and_role_collision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            documents = {
                "contract.json": {"criteria": [{"id": "C1"}]},
                "issues-manifest.json": {
                    "status": "approved",
                    "issues": [{"id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1", "story_refs": ["US-1"], "technical_enabler_for": [], "criterion_refs": ["C1"]}],
                },
                "scaffold-manifest.json": {
                    "status": "ready", "issue_id": "ISSUE-1",
                    "files": [{"path": "src/leaf.py", "pbs_leaf": "PBS-LEAF-1"}],
                },
                "model-bindings.json": {
                    "bindings": {
                        "reasoning_high": {"enabled": True, "model_id": "provider/architect"},
                        "implementation_general": {"enabled": True, "model_id": "provider/worker"},
                        "review_test": {"enabled": True, "model_id": "provider/test-owner"},
                        "review_acceptance": {"enabled": True, "model_id": "provider/acceptor"},
                    }
                },
            }
            for name, document in documents.items():
                (project / name).write_text(json.dumps(document) + "\n", encoding="utf-8")
            iteration = valid_iteration_contract()
            iteration["models"]["worker"] = "provider/acceptor"
            iteration["contract_sha256"] = hashlib.sha256((project / "contract.json").read_bytes()).hexdigest()
            iteration["issues_manifest_sha256"] = hashlib.sha256((project / "issues-manifest.json").read_bytes()).hexdigest()
            iteration["scaffold_manifest_sha256"] = hashlib.sha256((project / "scaffold-manifest.json").read_bytes()).hexdigest()
            (project / "iteration-contract.json").write_text(json.dumps(iteration) + "\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(VALIDATOR), "--project", str(project)], text=True, capture_output=True, check=False
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("worker model does not match implementation_general binding", result.stdout)
        self.assertIn("worker, test_owner, and acceptor model IDs must be distinct", result.stdout)

    def test_validator_rejects_internal_scope_and_budget_inconsistency(self) -> None:
        iteration = valid_iteration_contract()
        iteration.update({
            "story_refs": ["US-2"],
            "criterion_refs": ["C2"],
            "allowed_paths": ["../outside/**"],
            "allowed_commands": ["python3 -m unittest tests.test_leaf"],
            "verify_commands": ["python3 -m unittest tests.test_other"],
            "network_policy": {"mode": "deny", "allowed_hosts": ["example.test"]},
            "production_loc_target": 200,
            "production_loc_max": 100,
            "scaffold_files": ["src/other.py"],
        })

        result = self.run_validator(iteration)

        self.assertNotEqual(result.returncode, 0)
        for diagnostic in (
            "story_refs do not match approved issue",
            "criterion_refs do not match approved issue",
            "unknown contract criterion refs: C2",
            "unsafe allowed_paths entry",
            "verify_commands must be a subset of allowed_commands",
            "deny network policy requires empty allowed_hosts",
            "production LOC target exceeds max",
            "scaffold_files do not match scaffold manifest",
        ):
            self.assertIn(diagnostic, result.stdout)

    def test_validator_accepts_one_consistent_issue_and_pbs_leaf(self) -> None:
        result = self.run_validator(valid_iteration_contract())

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[iteration-contract] PASS", result.stdout)

    def test_scaffold_phase_owns_the_required_read_only_validator(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        descriptor_path = ROOT / "skills" / "scaffold" / "pipeline-validator.json"
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))

        self.assertEqual(machine["transitions"]["5.5"]["phase_process"], "scaffold")
        self.assertIs(descriptor["read_only"], True)
        self.assertEqual(descriptor["script"], "scripts/validate-iteration-contract.py")

    def test_every_scaffold_upstream_change_invalidates_iteration_contract(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        missing = sorted(
            upstream
            for upstream, consumers in machine["invalidations"].items()
            if "scaffold-manifest.json" in consumers and "iteration-contract.json" not in consumers
        )

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
