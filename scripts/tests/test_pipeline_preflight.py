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
    expected_signals = {
        "requirement_uncertainty",
        "knowledge_rarity",
        "interaction_density",
        "fidelity_need",
        "reversibility",
        "cost_of_error",
    }
    assert set(routing["task_signal_policy"]["signals"]) == expected_signals, "task signal policy drift"
    assert routing["task_signal_policy"]["selection_rules"], "task signal policy lacks selection rules"
    referenced_profiles = {
        profile
        for phase in routing["phases"].values()
        for profile in ([phase["profile"]] if "profile" in phase else []) + list(phase.get("roles", {}).values())
    }
    assert referenced_profiles <= known_profiles, f"unknown capability profiles: {referenced_profiles - known_profiles}"
    template_bindings = json.loads((ROOT / "templates/project/model-bindings.json").read_text(encoding="utf-8"))["bindings"]
    assert set(template_bindings) == known_profiles, "model binding template/profile drift"
    with tempfile.TemporaryDirectory() as raw:
        discovery_project = Path(raw)
        write(discovery_project, ".pipeline-state.json", json.loads((ROOT / "templates/project/.pipeline-state.json").read_text(encoding="utf-8")))
        write(discovery_project, "model-bindings.json", json.loads((ROOT / "templates/project/model-bindings.json").read_text(encoding="utf-8")))
        failures, _, _ = module.evaluate(ROOT, discovery_project, "-1")
        assert not failures, f"unclassified discovery must be runnable from any CLI: {failures}"
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
            "version": "2",
            "phase": "4c",
            "policy": {"risk_tier": "T2", "conditions": {"research_required": False, "frontend": False}},
            "model_bindings_file": "model-bindings.json",
            "artifacts": {
                "contract.json": {"sha256": contract_hash, "status": "ready", "invalidated_by": None},
                "judge-report.json": {"sha256": judge_hash, "status": "ready", "invalidated_by": None},
            },
            "human_gates": {
                "contract_locked": {"by": None, "at": None},
                "viz_before_tickets": {"by": None, "at": None},
                "human_acceptance": {"by": None, "at": None},
            }
        }
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert any("must equal 'PASS'" in item for item in failures), failures

        judge_hash = write(project, "judge-report.json", {"data": {"verdict": "PASS"}})
        ledger["artifacts"]["judge-report.json"]["sha256"] = judge_hash
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert not failures, failures

        failures, _, _ = module.evaluate(ROOT, project, "3")
        assert any("unnecessary" in item and "frontend" in item for item in failures), failures

        brief_hash = write(project, "product_brief.md", "brief\n")
        evidence_hash = write(project, "evidence-handoff.json", {"decision": "alpha", "spec_gaps": []})
        ledger["policy"] = {"risk_tier": "T2", "conditions": {"research_required": True, "frontend": False}}
        ledger["phase"] = "0"
        ledger["artifacts"].update({
            "product_brief.md": {"sha256": brief_hash, "status": "ready", "invalidated_by": None},
            "evidence-handoff.json": {"sha256": evidence_hash, "status": "ready", "invalidated_by": None},
        })
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "0")
        assert not failures, f"research must be available before delivery decision: {failures}"

        ledger["policy"] = {
            "risk_tier": "T0",
            "conditions": {"research_required": False, "frontend": False},
        }
        ledger["phase"] = "4c"
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert any("not on the T0 route" in item for item in failures), failures

        ledger["policy"] = {"risk_tier": "T2", "conditions": {"research_required": False, "frontend": False}}
        ledger["phase"] = "4c"
        ledger["artifacts"]["contract.json"]["sha256"] = "0" * 64
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4c")
        assert any("changed since attested" in item for item in failures), failures

        ledger["policy"]["risk_tier"] = "T4"
        ledger["phase"] = "4"
        ledger["artifacts"]["contract.json"]["sha256"] = contract_hash
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "4")
        assert any("risk-review.json" in item for item in failures), failures

        ledger["policy"]["risk_tier"] = "T3"
        ledger["phase"] = "6"
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
        ledger["model_bindings_file"] = "model-bindings.json"

        build_hash = write(project, "build-evidence.json", {
            "status": "complete",
            "checks": [{"command": "test", "status": "pass", "evidence_ref": "test.log"}],
            "criteria": [{"id": "C1", "status": "PASS", "evidence_ref": "test.log"}],
        })
        feature_hash = write(project, "feature-judge-report.json", {"data": {"verdict": "PASS"}})
        review_hash = write(project, "code-review.md", "**Overall assessment**: APPROVE\n")
        ledger["policy"] = {"risk_tier": "T2", "conditions": {"research_required": False, "frontend": False}}
        ledger["phase"] = "7"
        ledger["artifacts"].update({
            "build-evidence.json": {"sha256": build_hash, "status": "complete", "invalidated_by": None},
            "feature-judge-report.json": {"sha256": feature_hash, "status": "approved", "invalidated_by": None},
            "code-review.md": {"sha256": review_hash, "status": "approved", "invalidated_by": None},
        })
        ledger["human_gates"] = {
            "contract_locked": {"by": None, "at": None},
            "viz_before_tickets": {"by": None, "at": None},
            "human_acceptance": {"by": None, "at": None},
        }
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "7")
        assert not any("human_acceptance" in item for item in failures), failures
        failures, _, _ = module.evaluate(ROOT, project, "7", completion=True)
        assert any("human_acceptance" in item for item in failures), failures
        ledger["human_gates"]["human_acceptance"] = {"by": "owner", "at": "2026-07-17T00:00:00Z"}
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "7", completion=True)
        assert not failures, failures

        empty_build_hash = write(project, "build-evidence.json", {"status": "complete", "checks": [], "criteria": []})
        ledger["artifacts"]["build-evidence.json"]["sha256"] = empty_build_hash
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "7")
        assert any("requires at least one check" in item for item in failures), failures
        ledger["artifacts"]["build-evidence.json"]["sha256"] = build_hash
        write(project, "build-evidence.json", {
            "status": "complete",
            "checks": [{"command": "test", "status": "pass", "evidence_ref": "test.log"}],
            "criteria": [{"id": "C1", "status": "PASS", "evidence_ref": "test.log"}],
        })
        write(project, ".pipeline-state.json", ledger)

        ledger["artifacts"]["code-review.md"]["status"] = "draft"
        write(project, ".pipeline-state.json", ledger)
        failures, _, _ = module.evaluate(ROOT, project, "7", completion=True)
        assert any("still draft" in item for item in failures), failures

        open_gap = {
            "id": "SG-1",
            "kind": "ambiguity",
            "statement": "Two user-flow interpretations remain",
            "impact": "user_flow",
            "materiality": "blocking",
            "owner": "product-owner",
            "disposition": "prototype",
            "status": "open",
            "resolution_ref": None,
            "accepted_by": None,
            "evidence_refs": [],
        }
        failures = module.specification_gap_errors({"spec_gaps": [open_gap]})
        assert any("is unresolved" in item for item in failures), failures

        resolved_gap = {**open_gap, "status": "resolved", "resolution_ref": "prototype/SG-1.md"}
        assert module.specification_gap_errors({"spec_gaps": [resolved_gap]}) == []

        accepted_gap = {
            **open_gap,
            "status": "accepted",
            "disposition": "accept_risk",
            "resolution_ref": "ADR-12",
            "accepted_by": "owner@example.test",
        }
        assert module.specification_gap_errors({"spec_gaps": [accepted_gap]}) == []

        scoped_gap = {
            **open_gap,
            "status": "out_of_scope",
            "disposition": "out_of_scope",
            "resolution_ref": "product_brief.md#out-of-scope",
            "accepted_by": "owner@example.test",
        }
        assert module.specification_gap_errors({"spec_gaps": [scoped_gap]}) == []
    print("PASS pipeline semantic preflight tests")


if __name__ == "__main__":
    main()
