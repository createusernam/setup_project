#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Regression-test canonical User Story graph validation and flexible viewpoint readability review.
# SCOPE: Verify US → UC → criterion links, view references, and non-hard focal-element handling.
# DEPENDS: Python unittest, check-story-trace.py, and repository JSON schema validation.
# END_MODULE_CONTRACT
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "skills" / "visualization" / "scripts" / "check-story-trace.py"
SCHEMA = ROOT / "templates" / "project" / "viewpoint.schema.json"


class StoryTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        story_dir = self.project / "docs" / "stories"
        story_dir.mkdir(parents=True)
        (story_dir / "US-PAY.md").write_text("# US-PAY\n", encoding="utf-8")
        self.index = {
            "version": "1",
            "stories": [{
                "id": "US-PAY", "path": "docs/stories/US-PAY.md", "actor": "buyer",
                "goal": "pay", "trigger": "checkout", "outcome": "receipt",
                "boundaries": ["payment"], "use_cases": [{"id": "UC-PAY", "criterion_refs": ["C-PAY"]}],
                "assumptions": [], "open_questions": []
            }]
        }
        (story_dir / "index.json").write_text(json.dumps(self.index) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["python3", str(CHECKER), "--project", str(self.project)], text=True, capture_output=True, check=False)

    def test_valid_story_index_passes(self) -> None:
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_view_story_fails(self) -> None:
        views = self.project / "docs" / "views"
        views.mkdir()
        (views / "unknown.json").write_text(json.dumps({"story_ref": "US-MISSING"}) + "\n", encoding="utf-8")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown story", result.stdout)

    def test_view_without_story_fails(self) -> None:
        views = self.project / "docs" / "views"
        views.mkdir()
        (views / "missing.json").write_text(json.dumps({"story_ref": None}) + "\n", encoding="utf-8")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a story_ref", result.stdout)

    def test_issue_criteria_must_belong_to_its_referenced_story(self) -> None:
        self.index["stories"].append({
            "id": "US-SHIP", "path": "docs/stories/US-SHIP.md", "actor": "buyer",
            "goal": "receive", "trigger": "paid", "outcome": "delivery",
            "boundaries": ["shipping"], "use_cases": [{"id": "UC-SHIP", "criterion_refs": ["C-SHIP"]}],
            "assumptions": [], "open_questions": []
        })
        (self.project / "docs" / "stories" / "US-SHIP.md").write_text("# US-SHIP\n", encoding="utf-8")
        (self.project / "docs" / "stories" / "index.json").write_text(json.dumps(self.index) + "\n", encoding="utf-8")
        (self.project / "issues-manifest.json").write_text(json.dumps({
            "issues": [{"id": "ISSUE-1", "pbs_leaf": "PBS-1", "story_refs": ["US-PAY"],
                        "technical_enabler_for": [], "criterion_refs": ["C-SHIP"]}]
        }) + "\n", encoding="utf-8")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("criteria outside its referenced stories", result.stdout)

    def test_completed_evidence_must_cover_every_issue_criterion(self) -> None:
        (self.project / "issues-manifest.json").write_text(json.dumps({
            "issues": [{"id": "ISSUE-1", "pbs_leaf": "PBS-1", "story_refs": ["US-PAY"],
                        "technical_enabler_for": [], "criterion_refs": ["C-PAY"]}]
        }) + "\n", encoding="utf-8")
        (self.project / "build-evidence.json").write_text(json.dumps({
            "status": "complete", "issue_id": "ISSUE-1", "pbs_leaf": "PBS-1", "criteria": []
        }) + "\n", encoding="utf-8")
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not cover issue criteria", result.stdout)

    def test_more_than_three_focal_elements_need_reason_not_rejection(self) -> None:
        spec = ROOT / "scripts" / "json_schema.py"
        namespace: dict[str, object] = {}
        exec(spec.read_text(encoding="utf-8"), namespace)
        document = {
            "$schema": "../../viewpoint.schema.json", "version": "1", "view_id": "capacity",
            "stakeholder": "owner", "decision": "choose", "story_ref": "US-PAY", "concern": "flow_and_overflow",
            "scale": "system", "focal_elements": ["a", "b", "c", "d"], "aggregation_rationale": "one queue decision",
            "actors": ["owner"], "metaphor": None, "canonical_refs": ["contract.json"], "hidden_aggregation": [],
            "next_scale_views": [], "approval": {"status": "draft", "by": None, "at": None}
        }
        errors = namespace["validate"](document, json.loads(SCHEMA.read_text(encoding="utf-8")))
        self.assertEqual(errors, [])
        document.pop("aggregation_rationale")
        self.assertTrue(namespace["validate"](document, json.loads(SCHEMA.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
