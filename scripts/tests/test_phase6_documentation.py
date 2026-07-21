#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test synchronization of Phase 6 executable gates, artifact lineage, roles, and human supervision docs.
# SCOPE: Cross-check run.sh, skills, machine contract, human/agent docs, and pm-review output vocabulary.
# DEPENDS: Python unittest and repository text/JSON contracts.
# END_MODULE_CONTRACT
from __future__ import annotations

import json
import hashlib
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class Phase6DocumentationTests(unittest.TestCase):
    def test_build_loop_run_script_enforces_declared_static_and_runtime_gates(self) -> None:
        run = (ROOT / "skills/build-loop/scripts/run.sh").read_text(encoding="utf-8")
        for token in (
            "validate-prerequisites.py", "setup-preflight 6", "setup-grace-lint --profile autonomous",
            "BUILD_LOOP_PLAYWRIGHT_READY", "BUILD_LOOP_DEV_SERVER_READY", "iteration-contract.json",
        ):
            self.assertIn(token, run)

    def test_pbs_leaf_lineage_is_documented_across_every_producer_consumer(self) -> None:
        paths = (
            "docs/human/PIPELINE.md", "docs/agent/ARTIFACT-CONTRACTS.md",
            "skills/to-issues/SKILL.md", "skills/scaffold/SKILL.md", "skills/build-loop/SKILL.md",
        )
        for relative in paths:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("PBS leaf", text, relative)
        contracts = (ROOT / "docs/agent/ARTIFACT-CONTRACTS.md").read_text(encoding="utf-8")
        for artifact in ("issues-manifest.json", "scaffold-manifest.json", "iteration-contract.json", "build-evidence.json"):
            self.assertIn(artifact, contracts)

    def test_pm_review_declared_checks_exactly_match_output(self) -> None:
        skill = (ROOT / "skills/pm-review/SKILL.md").read_text(encoding="utf-8")
        guide = re.search(r"<guide>(.*?)</guide>", skill, re.S).group(1)
        output = re.search(r'<output_format>\s*\{(.*?)\}\s*</output_format>', skill, re.S).group(1)
        guide_count = len(re.findall(r"^\d+\. \*\*", guide, re.M))
        checks_body = re.search(r'"checks": \{(.*?)\n  \}', output, re.S).group(1)
        output_checks = re.findall(r'"([a-z_]+)": true', checks_body)
        self.assertEqual(guide_count, 8)
        self.assertEqual(len(output_checks), 8)
        self.assertIn("eight checks", skill.lower())

    def test_phase6_roles_and_dashboard_match_machine_orchestration(self) -> None:
        machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
        routing = json.loads((ROOT / "model-routing.json").read_text(encoding="utf-8"))
        self.assertEqual(set(routing["phases"]["6"]["roles"]), {"architect", "implementer", "test_owner", "acceptor"})
        required = {item["artifact"] for item in machine["transitions"]["7"]["requires"]}
        self.assertTrue({"iteration-budget.json", "scaffold-integrity.json", "iteration-review.json", "iteration-dashboard.json", "build-evidence.json"}.issubset(required))
        for relative in ("docs/human/PIPELINE.md", "docs/agent/ARTIFACT-CONTRACTS.md", "docs/agent/COMPAT.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("worker → mechanical checks → architect → test owner → isolated acceptor", text, relative)
        visualization = (ROOT / "skills/visualization/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("[Current iteration dashboard](dashboard.md)", visualization)
        self.assertIn("iteration-dashboard.json", visualization)


class BuildLoopPrerequisiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = ROOT / "skills/build-loop/scripts/validate-prerequisites.py"
        spec = importlib.util.spec_from_file_location("build_loop_prerequisites", path)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.module)

    def make_project(self, root: Path) -> dict:
        contract = {
            "is_frontend": False,
            "is_backend": True,
            "integrations": {"data_flow": "request to store", "frontend_calls": [], "backend_endpoints": ["POST /items"]},
            "criteria": [
                {"id": f"c{index}", "must_pass": index == 0, "verify": {"method": "test"}}
                for index in range(10)
            ],
        }
        encoded = (json.dumps(contract, sort_keys=True) + "\n").encode()
        (root / "contract.json").write_bytes(encoded)
        (root / ".contract-attestation").write_text(hashlib.sha256(encoded).hexdigest() + "\n")
        (root / "iteration-contract.json").write_text(json.dumps({"status": "ready"}) + "\n")
        return contract

    def test_valid_static_prerequisites_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            self.assertEqual(self.module.validate(root), [])

    def test_partial_contract_and_manual_must_pass_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = self.make_project(root)
            contract["criteria"][0]["verify"]["method"] = "manual"
            encoded = (json.dumps(contract, sort_keys=True) + "\n").encode()
            (root / "contract.json").write_bytes(encoded)
            (root / ".contract-attestation").write_text(hashlib.sha256(encoded).hexdigest() + "\n")
            errors = self.module.validate(root)
            self.assertTrue(any("cannot use manual" in error for error in errors))

            contract["criteria"].pop()
            encoded = (json.dumps(contract, sort_keys=True) + "\n").encode()
            (root / "contract.json").write_bytes(encoded)
            (root / ".contract-attestation").write_text(hashlib.sha256(encoded).hexdigest() + "\n")
            errors = self.module.validate(root)
            self.assertTrue(any("at least 10" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
