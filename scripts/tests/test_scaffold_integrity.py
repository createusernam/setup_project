#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test trusted pre/post scaffold and GRACE anchor integrity checks.
# SCOPE: Cover preserved implementations, contract/block/log drift, IMPL gaps, baseline hashes, and new modules.
# DEPENDS: Python unittest, git, and build-loop scaffold-integrity checker.
# END_MODULE_CONTRACT
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "skills" / "build-loop" / "scripts" / "check-scaffold-integrity.py"
SCHEMA = ROOT / "templates" / "project" / "scaffold-integrity.schema.json"


BASELINE = """# START_MODULE_CONTRACT
# PURPOSE: Implement one leaf.
# SCOPE: One operation.
# DEPENDS: none.
# END_MODULE_CONTRACT

# START_CONTRACT: run_leaf
# PURPOSE: Run it.
# INPUTS: none.
# OUTPUTS: int.
# SIDE_EFFECTS: log.
# END_CONTRACT: run_leaf
def run_leaf():
    # START_BLOCK_RUN
    logger.info("[Leaf][run_leaf][RUN] start")
    # IMPL: return the approved value for criterion C1.
    raise RuntimeError("NOT_IMPLEMENTED: RUN")
    # END_BLOCK_RUN
"""


def digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def hashes(text: str, path: str) -> dict[str, str]:
    module = re.search(r"(?ms)^.*START_MODULE_CONTRACT.*?$.*?^.*END_MODULE_CONTRACT.*?$", text).group(0)
    function = re.search(r"(?ms)^.*START_CONTRACT:\s*run_leaf\s*$.*?^.*END_CONTRACT:\s*run_leaf\s*$", text).group(0)
    block = re.search(r"(?ms)^.*START_BLOCK_RUN\s*$.*?^.*END_BLOCK_RUN\s*$", text).group(0)
    block_payload = [line.strip() for line in block.splitlines() if "START_BLOCK_" in line or "IMPL:" in line or "END_BLOCK_" in line]
    logs = re.findall(r"\[[^]\n]+\]\[[^]\n]+\]\[[^]\n]+\]", text)
    structure = {"module": module, "functions": [["run_leaf", function]], "blocks": [["RUN", block_payload]], "logs": logs}
    return {
        f"{path}#MODULE_CONTRACT": digest(module),
        f"{path}#FUNCTION_CONTRACT:run_leaf": digest(function),
        f"{path}#BLOCK:RUN": digest(block_payload),
        f"{path}#LOG_ANCHORS": digest(logs),
        f"{path}#SCAFFOLD_STRUCTURE": digest(structure),
    }


class ScaffoldIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "tests@example.invalid")
        self.git("config", "user.name", "Integrity Tests")
        source = self.project / "src" / "leaf.py"
        source.parent.mkdir()
        source.write_text(BASELINE, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "scaffold")
        self.baseline = self.git("rev-parse", "HEAD").stdout.strip()
        self.write_contract(hashes(BASELINE, "src/leaf.py"))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.project, text=True, capture_output=True, check=True)

    def write_contract(self, anchor_hashes: dict[str, str]) -> None:
        contract = {
            "status": "ready", "issue_id": "ISSUE-1", "pbs_leaf": "PBS-LEAF-1",
            "baseline_commit": self.baseline, "scaffold_files": ["src/leaf.py"],
            "contract_anchor_hashes": anchor_hashes,
        }
        (self.project / "iteration-contract.json").write_text(json.dumps(contract) + "\n", encoding="utf-8")
        self.git("add", "iteration-contract.json")
        self.git("commit", "-qm", "iteration contract", "--allow-empty")

    def check(self) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            ["python3", str(CHECKER), "--project", str(self.project)],
            text=True, capture_output=True, check=False,
        )
        path = self.project / "scaffold-integrity.json"
        return result, json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def test_orchestrator_state_scripts_are_not_treated_as_new_modules(self) -> None:
        helper = self.project / ".build-loop" / "iterations" / "1" / "traces"
        helper.mkdir(parents=True)
        (helper / "capture.sh").write_text("echo trace\n", encoding="utf-8")

        result, report = self.check()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["violations"], [])

    def test_worktree_iteration_contract_differing_from_head_is_rejected(self) -> None:
        contract = json.loads((self.project / "iteration-contract.json").read_text(encoding="utf-8"))
        contract["scaffold_files"] = []
        (self.project / "iteration-contract.json").write_text(json.dumps(contract) + "\n", encoding="utf-8")

        result, report = self.check()

        self.assertEqual(result.returncode, 1)
        self.assertIn("committed", result.stdout)
        self.assertEqual(report, {})

    def test_implementation_body_may_change_without_anchor_drift(self) -> None:
        current = BASELINE.replace('raise RuntimeError("NOT_IMPLEMENTED: RUN")', "return 1")
        (self.project / "src" / "leaf.py").write_text(current, encoding="utf-8")

        result, report = self.check()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["violations"], [])

    def test_module_function_block_and_log_drift_fail_closed(self) -> None:
        current = BASELINE.replace("PURPOSE: Implement one leaf.", "PURPOSE: Expand scope.")
        current = current.replace("START_CONTRACT: run_leaf", "START_CONTRACT: renamed")
        current = current.replace("END_CONTRACT: run_leaf", "END_CONTRACT: renamed")
        current = current.replace("START_BLOCK_RUN", "START_BLOCK_OTHER").replace("END_BLOCK_RUN", "END_BLOCK_OTHER")
        current = current.replace("[Leaf][run_leaf][RUN]", "[Leaf][run_leaf][OTHER]")
        (self.project / "src" / "leaf.py").write_text(current, encoding="utf-8")

        result, report = self.check()

        self.assertEqual(result.returncode, 5)
        self.assertEqual(report["verdict"], "SCAFFOLD_DRIFT")
        types = {item["type"] for item in report["violations"]}
        self.assertTrue({"module_contract_changed", "function_contract_changed", "block_anchor_changed", "log_anchor_changed"}.issubset(types))

    def test_impl_directive_change_routes_architecture_gap_upstream(self) -> None:
        current = BASELINE.replace("return the approved value", "invent a different interface and value")
        (self.project / "src" / "leaf.py").write_text(current, encoding="utf-8")

        result, report = self.check()

        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["verdict"], "CONTRACT_GAP")
        self.assertEqual(report["gap"]["type"], "architecture_gap")
        self.assertEqual(report["gap"]["owning_phase"], "5.5")
        self.assertIn("impl_directive_changed", {item["type"] for item in report["violations"]})

    def test_contract_hash_that_does_not_match_baseline_is_contract_gap(self) -> None:
        wrong = hashes(BASELINE, "src/leaf.py")
        wrong["src/leaf.py#MODULE_CONTRACT"] = "0" * 64
        self.write_contract(wrong)

        result, report = self.check()

        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["verdict"], "CONTRACT_GAP")
        self.assertIn("original_hash_mismatch", {item["type"] for item in report["violations"]})

    def test_new_source_file_without_module_contract_is_scaffold_drift(self) -> None:
        (self.project / "src" / "extra.py").write_text("def surprise():\n    return 1\n", encoding="utf-8")

        result, report = self.check()

        self.assertEqual(result.returncode, 5)
        self.assertEqual(report["verdict"], "SCAFFOLD_DRIFT")
        self.assertIn("new_file_missing_module_contract", {item["type"] for item in report["violations"]})

    def test_report_is_schema_valid_and_deterministic(self) -> None:
        (self.project / "src" / "leaf.py").write_text(BASELINE.replace("NOT_IMPLEMENTED: RUN", "implemented"), encoding="utf-8")
        first, report = self.check()
        first_bytes = (self.project / "scaffold-integrity.json").read_bytes()
        second, second_report = self.check()

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(report, second_report)
        self.assertEqual(first_bytes, (self.project / "scaffold-integrity.json").read_bytes())
        self.assertTrue(SCHEMA.is_file())
        self.assertEqual(report["producer"], "trusted-scaffold-integrity-checker")
        self.assertIn("phase6-semantic-validator", report["consumers"])

    def test_snapshot_prints_exact_hashes_for_contract_producer(self) -> None:
        result = subprocess.run(
            ["python3", str(CHECKER), "--project", str(self.project), "--snapshot"],
            text=True, capture_output=True, check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), hashes(BASELINE, "src/leaf.py"))


if __name__ == "__main__":
    unittest.main()
