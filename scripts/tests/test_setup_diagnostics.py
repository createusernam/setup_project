#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Protect structured setup diagnostics, reproducible tool pins, and portable content paths.
# SCOPE: Test OpenCode instruction parsing, toolchain reference checks, and user-home leakage guards.
# DEPENDS: Python unittest and standard library.
# END_MODULE_CONTRACT
"""Regression tests for setup diagnostics and portability."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def load(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OPENCODE = load("check-opencode-config.py")


class OpenCodeConfigTests(unittest.TestCase):
    def test_requires_valid_json_array_and_both_exact_paths(self) -> None:
        cases = (
            ("not json", "invalid JSON"),
            (json.dumps({"instructions": str(ROOT / "docs" / "human" / "PIPELINE.md")}), "array"),
            (json.dumps({"instructions": [str(ROOT / "docs" / "human" / "PIPELINE.md")]}), "COMPAT"),
            (json.dumps({"comment": str(ROOT / "docs" / "human" / "PIPELINE.md"), "instructions": []}), "PIPELINE"),
        )
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "opencode.json"
            for content, expected in cases:
                with self.subTest(expected=expected):
                    config.write_text(content, encoding="utf-8")
                    lines, errors = OPENCODE.check(config, ROOT)
                    self.assertTrue(errors)
                    self.assertIn(expected, "\n".join(lines + errors))

            config.write_text(json.dumps({"instructions": [
                str(ROOT / "docs" / "human" / "PIPELINE.md"),
                str(ROOT / "docs" / "agent" / "COMPAT.md"),
            ]}), encoding="utf-8")
            _, errors = OPENCODE.check(config, ROOT)
            self.assertEqual(errors, [])


class PortabilityAndPinTests(unittest.TestCase):
    def test_toolchain_references_match_manifest(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check-toolchain-versions.py")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installable_content_has_no_user_specific_home_path(self) -> None:
        pattern = re.compile(r"/home/(?!you(?:/|\b)|\.\.\.(?:/|\b))[A-Za-z0-9._-]+/")
        hits: list[str] = []
        roots = [ROOT / "docs" / "human", ROOT / "docs" / "agent", ROOT / "skills"]
        for base in roots:
            for path in base.rglob("*"):
                if path.is_file() and path.suffix in {".md", ".py", ".sh", ".json"}:
                    if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                        hits.append(str(path.relative_to(ROOT)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
