#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Protect cross-runtime skill linking, routing-policy installation, and collision migration.
# SCOPE: Test managed blocks, discovery failures, successful dual roots, and installer all-or-none behavior.
# DEPENDS: Python unittest, the standard library, and setup installer/discovery scripts.
# END_MODULE_CONTRACT
"""Regression tests for cross-runtime skill discovery."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = REPO / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUTING = load_script("install-skill-routing.py")
DISCOVERY = load_script("check-skill-discovery.py")


class SkillRoutingTests(unittest.TestCase):
    def test_managed_block_preserves_content_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "CLAUDE.md"
            target.write_text("# Personal rules\n", encoding="utf-8")
            managed = "<!-- setup:skill-routing:start -->\npolicy\n<!-- setup:skill-routing:end -->"

            ROUTING.install_one(target, managed)
            first = target.read_text(encoding="utf-8")
            ROUTING.install_one(target, managed)

            self.assertEqual(target.read_text(encoding="utf-8"), first)
            self.assertIn("# Personal rules", first)
            self.assertEqual(first.count(ROUTING.START), 1)

    def test_symlinked_opencode_and_claude_rules_share_one_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            claude = home / ".claude" / "CLAUDE.md"
            claude.parent.mkdir(parents=True)
            claude.write_text("rules\n", encoding="utf-8")
            opencode = home / ".config" / "opencode" / "AGENTS.md"
            opencode.parent.mkdir(parents=True)
            opencode.symlink_to(claude)

            targets = ROUTING.unique_targets(home)

            self.assertEqual(len(targets), 2)  # Claude+OpenCode share one; Codex is separate.
            self.assertTrue(any(set(names) == {"claude", "opencode"} for names, _ in targets))


class SkillDiscoveryTests(unittest.TestCase):
    def make_setup(self, root: Path) -> Path:
        setup = root / "setup"
        skill = setup / "skills" / "alpha"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: alpha\ndescription: Test.\n---\n", encoding="utf-8")
        scripts = setup / "scripts"
        scripts.mkdir()
        (scripts / "install-skill-routing.py").write_text(
            (REPO / "scripts" / "install-skill-routing.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        docs = setup / "docs" / "agent"
        docs.mkdir(parents=True)
        (docs / "SKILL-ROUTING.md").write_text("routing", encoding="utf-8")
        return setup

    def install_routing(self, setup: Path, home: Path) -> None:
        managed = ROUTING.managed_text(setup / "docs" / "agent" / "SKILL-ROUTING.md")
        for _, target in ROUTING.unique_targets(home):
            ROUTING.install_one(target, managed)

    def test_reports_missing_real_and_wrong_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup = self.make_setup(root)
            home = root / "home"
            real = home / ".claude" / "skills" / "alpha"
            real.mkdir(parents=True)
            wrong_source = root / "wrong"
            wrong_source.mkdir()
            wrong = home / ".agents" / "skills" / "alpha"
            wrong.parent.mkdir(parents=True)
            wrong.symlink_to(wrong_source)
            self.install_routing(setup, home)

            errors, _ = DISCOVERY.check_discovery(setup, home)

            self.assertTrue(any("real path shadows" in error for error in errors), errors)
            self.assertTrue(any("points to" in error for error in errors), errors)

    def test_two_roots_and_routing_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup = self.make_setup(root)
            home = root / "home"
            source = setup / "skills" / "alpha"
            for runtime_root in (home / ".claude" / "skills", home / ".agents" / "skills"):
                runtime_root.mkdir(parents=True)
                (runtime_root / "alpha").symlink_to(source)
            self.install_routing(setup, home)

            errors, _ = DISCOVERY.check_discovery(setup, home)

            self.assertEqual(errors, [])


class InstallerIntegrationTests(unittest.TestCase):
    def test_collision_is_all_or_none_then_migrated_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            stale = home / ".agents" / "skills" / "planning-with-files"
            stale.mkdir(parents=True)
            (stale / "keep.txt").write_text("user data", encoding="utf-8")
            bindir = home / "bin"
            env = {**os.environ, "HOME": str(home), "WORKCTL_BIN_DIR": str(bindir), "PATH": "/usr/bin:/bin"}

            refused = subprocess.run(
                ["bash", str(REPO / "install.sh")], env=env, text=True, capture_output=True, check=False
            )
            self.assertEqual(refused.returncode, 1, refused.stdout + refused.stderr)
            self.assertFalse((home / ".claude" / "skills" / "startup").exists())
            self.assertEqual((stale / "keep.txt").read_text(encoding="utf-8"), "user data")

            migrated = subprocess.run(
                ["bash", str(REPO / "install.sh"), "--migrate-skill-collisions"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
            expected = (REPO / "skills" / "planning-with-files").resolve()
            self.assertEqual(stale.resolve(), expected)
            self.assertEqual((home / ".claude" / "skills" / "planning-with-files").resolve(), expected)
            expected_commands = {
                "workctl": REPO / "scripts" / "workctl.py",
                "setup-skill-doctor": REPO / "scripts" / "check-skill-discovery.py",
                "setup-pipeline": REPO / "scripts" / "pipeline-state.py",
                "setup-preflight": REPO / "scripts" / "pipeline-preflight.sh",
                "setup-model-check": REPO / "scripts" / "model-check.sh",
                "setup-grace-lint": REPO / "scripts" / "grace-lint.sh",
            }
            for command, source in expected_commands.items():
                self.assertEqual((bindir / command).resolve(), source.resolve())
            backups = list((home / ".setup-skill-backups").glob("*/agents/planning-with-files/keep.txt"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "user data")


if __name__ == "__main__":
    unittest.main()
