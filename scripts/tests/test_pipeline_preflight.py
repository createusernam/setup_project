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
    assert machine["transitions"]["-1"]["skill"] == "discovery process", "public phase -1 must not require a private skill"
    assert not any("requires" in phase or "human_gate" in phase for phase in routing["phases"].values()), "transition truth leaked back into model routing"
    serialized_routing = json.dumps(routing).lower()
    for concrete_name in ("op" + "us", "son" + "net", "deep" + "seek", "g" + "lm", "gem" + "ini", "g" + "rok"):
        assert concrete_name not in serialized_routing, f"concrete model leaked into capability routing: {concrete_name}"
    legacy_field = "required_" + "model"
    assert not any(legacy_field in phase for phase in routing["phases"].values()), "legacy concrete routing field present"
    known_profiles = set(routing["profiles"])
    referenced_profiles = {
        profile
        for phase in routing["phases"].values()
        for profile in ([phase["profile"]] if "profile" in phase else []) + list(phase.get("roles", {}).values())
    }
    assert referenced_profiles <= known_profiles, f"unknown capability profiles: {referenced_profiles - known_profiles}"
    template_bindings = json.loads((ROOT / "templates/project/model-bindings.json").read_text(encoding="utf-8"))["bindings"]
    assert set(template_bindings) == known_profiles, "model binding template/profile drift"
    with tempfile.TemporaryDirectory() as raw:
        project = Path(raw)
        write(project, "model-bindings.json", {
            "version": "1",
            "bindings": {
                "reasoning_high": {"runtime": "claude", "model_id": "model-reasoning-high", "enabled": True},
                "reasoning_balanced": {"runtime": "claude", "model_id": "model-reasoning-balanced", "enabled": True},
                "research_worker": {"runtime": "codex", "model_id": "model-research", "enabled": True},
                "implementation_general": {"runtime": "codex", "model_id": "model-implementation", "enabled": True},
                "implementation_ui": {"runtime": "opencode", "model_id": "model-ui", "enabled": True},
                "review_test": {"runtime": "opencode", "model_id": "model-test", "enabled": True},
                "review_acceptance": {"runtime": "claude", "model_id": "model-acceptance", "enabled": True},
            }
        })
        contract_hash = write(project, "contract.json", {"scope": "x"})
        judge_hash = write(project, "judge-report.json", {"data": {"verdict": "FAIL"}})
        ledger = {
            "policy": {"risk_tier": "T2", "skipped_gates": []},
            "model_bindings_file": "model-bindings.json",
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

        ledger["policy"]["risk_tier"] = "T3"
        bindings = json.loads((project / "model-bindings.json").read_text(encoding="utf-8"))
        bindings["bindings"]["review_test"]["model_id"] = "model-implementation"
        write(project, "model-bindings.json", bindings)
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "6")
        assert any("must resolve to different model IDs" in item for item in failures), failures

        bindings["bindings"]["review_test"] = {"runtime": "typo-runtime", "model_id": "model-test", "enabled": True}
        write(project, "model-bindings.json", bindings)
        failures, _, _ = module.evaluate(ROOT, project, "6")
        assert any("review_test" in item and "unbound or disabled" in item for item in failures), failures

        ledger["model_bindings_file"] = "../outside.json"
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "6")
        assert any("model_bindings_file" in item and "project-relative" in item for item in failures), failures
    print("PASS pipeline semantic preflight tests")


if __name__ == "__main__":
    main()
