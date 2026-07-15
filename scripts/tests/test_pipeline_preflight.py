#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test semantic pipeline transitions, risk policy, and impossible judge/viz ordering.
# SCOPE: Exercise the Python evaluator with temporary project ledgers and artifacts.
# DEPENDS: Python standard library and scripts/pipeline_preflight.py.
# END_MODULE_CONTRACT
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("pipeline_preflight", ROOT / "scripts" / "pipeline_preflight.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def write(project: Path, name: str, value: object) -> str:
    path = project / name
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value) + "\n" if not isinstance(value, str) else value
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode()).hexdigest()


def main() -> None:
    machine = json.loads((ROOT / "pipeline-machine.json").read_text(encoding="utf-8"))
    routing = json.loads((ROOT / "model-routing.json").read_text(encoding="utf-8"))
    assert set(machine["transitions"]) == set(routing["phases"]), "machine/model phase drift"
    assert not any("requires" in phase or "human_gate" in phase for phase in routing["phases"].values()), "transition truth leaked back into model routing"
    with tempfile.TemporaryDirectory() as raw:
        project = Path(raw)
        contract_hash = write(project, "contract.json", {"scope": "x"})
        judge_hash = write(project, "judge-report.json", {"data": {"verdict": "FAIL"}})
        ledger = {
            "policy": {"risk_tier": "T2", "skipped_gates": []},
            "models_available": ["opus", "sonnet", "deepseek-v4", "glm"],
            "artifacts": {"contract.json": {"sha256": contract_hash}, "judge-report.json": {"sha256": judge_hash}},
            "human_gates": {}
        }
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert any("must equal 'PASS'" in item for item in failures), failures

        judge_hash = write(project, "judge-report.json", {"data": {"verdict": "PASS"}})
        ledger["artifacts"]["judge-report.json"]["sha256"] = judge_hash
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert not failures, failures

        ledger["policy"] = {
            "risk_tier": "T0",
            "skipped_gates": [{"phase": "4c", "reason": "not needed", "approved_by": "owner", "approved_at": "2026-07-15"}],
        }
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert any("not on the T0 route" in item for item in failures), failures

        ledger["policy"] = {"risk_tier": "T2", "skipped_gates": []}
        ledger["artifacts"]["contract.json"]["sha256"] = "0" * 64
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert any("changed since attested" in item for item in failures), failures

        ledger["policy"]["risk_tier"] = "T4"
        ledger["artifacts"]["contract.json"]["sha256"] = contract_hash
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4")
        assert any("risk-review.json" in item for item in failures), failures
    print("PASS pipeline semantic preflight tests")


if __name__ == "__main__":
    main()
