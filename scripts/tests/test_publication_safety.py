#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Prove public publishing validates target identity and keeps dry-run targets byte-stable.
# SCOPE: Exercise publisher path guards, remote guards, preview behavior, and ordinary publication.
# DEPENDS: Python unittest, bash, git, rsync, and the repository publisher.
# END_MODULE_CONTRACT
"""Behavioral safety tests for publish-public.sh."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def run(*command: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def git(cwd: Path, *arguments: str) -> None:
    result = run("git", *arguments, cwd=cwd)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and ".git" not in item.parts):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@unittest.skipUnless((ROOT / "publish-public.sh").is_file(), "private publisher is excluded from the public mirror")
class PublisherSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.source = self.root / "private"
        (self.source / "docs" / "human").mkdir(parents=True)
        (self.source / "docs" / "agent").mkdir(parents=True)
        shutil.copy2(ROOT / "publish-public.sh", self.source / "publish-public.sh")
        marker = "<!-- setup:public-projection-rule -->\n"
        (self.source / "docs" / "human" / "SETUP.md").write_text(marker, encoding="utf-8")
        (self.source / "docs" / "agent" / "COMPAT.md").write_text(marker, encoding="utf-8")
        (self.source / "README.md").write_text("private source projection\n", encoding="utf-8")
        git(self.source, "init", "-b", "main")
        git(self.source, "config", "user.name", "Publisher Test")
        git(self.source, "config", "user.email", "publisher@example.test")
        git(self.source, "add", ".")
        git(self.source, "commit", "-m", "source")

        seed = self.root / "seed"
        seed.mkdir()
        git(seed, "init", "-b", "main")
        git(seed, "config", "user.name", "Publisher Test")
        git(seed, "config", "user.email", "publisher@example.test")
        (seed / "README.md").write_text("old public tree\n", encoding="utf-8")
        git(seed, "add", ".")
        git(seed, "commit", "-m", "seed")
        self.origin = self.root / "public.git"
        git(self.root, "clone", "--bare", str(seed), str(self.origin))
        self.target = self.root / "public-checkout"
        git(self.root, "clone", str(self.origin), str(self.target))
        git(self.target, "config", "user.name", "Publisher Test")
        git(self.target, "config", "user.email", "publisher@example.test")
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "SETUP_PUBLIC_REPO": str(self.origin),
            "GIT_AUTHOR_NAME": "Publisher Test",
            "GIT_AUTHOR_EMAIL": "publisher@example.test",
            "GIT_COMMITTER_NAME": "Publisher Test",
            "GIT_COMMITTER_EMAIL": "publisher@example.test",
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def publish(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return run("bash", "publish-public.sh", *arguments, cwd=self.source, env=self.env)

    def test_dry_run_leaves_correct_target_unchanged(self) -> None:
        before = digest_tree(self.target)
        head_before = run("git", "rev-parse", "HEAD", cwd=self.target).stdout

        result = self.publish("--dry-run", str(self.target))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("target unchanged", result.stdout)
        self.assertEqual(digest_tree(self.target), before)
        self.assertEqual(run("git", "rev-parse", "HEAD", cwd=self.target).stdout, head_before)
        self.assertEqual(run("git", "status", "--porcelain", cwd=self.target).stdout, "")

    def test_rejects_source_descendant_and_wrong_remote_before_writing(self) -> None:
        for unsafe in (self.source, self.source / "nested", self.root):
            with self.subTest(target=unsafe):
                result = self.publish("--dry-run", str(unsafe))
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("private source", result.stderr)

        unrelated_origin = self.root / "unrelated.git"
        git(self.root, "clone", "--bare", str(self.origin), str(unrelated_origin))
        unrelated = self.root / "unrelated"
        git(self.root, "clone", str(unrelated_origin), str(unrelated))
        before = digest_tree(unrelated)
        result = self.publish("--dry-run", str(unrelated))
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("origin does not match", result.stderr)
        self.assertEqual(digest_tree(unrelated), before)

    def test_normal_publish_updates_only_the_public_mirror(self) -> None:
        result = self.publish(str(self.target))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.target / "README.md").read_text(encoding="utf-8"), "private source projection\n")
        self.assertFalse((self.target / "publish-public.sh").exists())
        self.assertEqual(run("git", "status", "--porcelain", cwd=self.target).stdout, "")


if __name__ == "__main__":
    unittest.main()
