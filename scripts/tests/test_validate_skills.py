#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Protect runtime-aware skill validation from accepting malformed or misprofiled frontmatter.
# SCOPE: Test Claude fields, portable-profile rejection, invalid YAML, and directory/name matching.
# DEPENDS: Python unittest, PyYAML, and scripts/validate-skills.py.
# END_MODULE_CONTRACT
"""Regression tests for validate-skills.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "validate-skills.py"
SPEC = importlib.util.spec_from_file_location("validate_skills", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SkillValidationTests(unittest.TestCase):
    def write_skill(self, root: Path, name: str, frontmatter: str) -> Path:
        directory = root / name
        directory.mkdir()
        path = directory / "SKILL.md"
        path.write_text(f"---\n{frontmatter}\n---\n\n# Skill\n", encoding="utf-8")
        return path

    def test_claude_profile_accepts_user_invocable_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_skill(
                Path(directory),
                "example-skill",
                """name: example-skill
description: A sufficiently descriptive skill trigger for validation tests and routing.
user-invocable: true
hooks:
  Stop:
    - hooks: []""",
            )
            self.assertEqual(MODULE.validate_skill(path, "claude"), [])

    def test_portable_profile_rejects_claude_only_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_skill(
                Path(directory),
                "example-skill",
                """name: example-skill
description: A sufficiently descriptive skill trigger for validation tests and routing.
user-invocable: true""",
            )
            self.assertIn("unsupported portable key(s): user-invocable", MODULE.validate_skill(path, "portable"))

    def test_invalid_unquoted_colon_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_skill(
                Path(directory),
                "example-skill",
                """name: example-skill
description: Invalid scalar: this colon makes the YAML ambiguous and must fail validation.""",
            )
            errors = MODULE.validate_skill(path, "claude")
            self.assertTrue(any(error.startswith("invalid YAML:") for error in errors), errors)

    def test_name_must_match_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_skill(
                Path(directory),
                "directory-name",
                """name: different-name
description: A sufficiently descriptive skill trigger for validation tests and routing.""",
            )
            self.assertIn("name 'different-name' does not match directory 'directory-name'", MODULE.validate_skill(path, "claude"))


if __name__ == "__main__":
    unittest.main()
