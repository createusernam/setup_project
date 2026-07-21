#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Protect cross-runtime task selection, handoff, checkpoint, lease, and launch behavior.
# SCOPE: Exercise workctl in temporary git repositories with fake runtime executables and no network access.
# DEPENDS: Python unittest, git, and scripts/workctl.py.
# END_MODULE_CONTRACT
"""Regression tests for workctl."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "workctl.py"
SPEC = importlib.util.spec_from_file_location("workctl", SCRIPT)
assert SPEC and SPEC.loader
WORKCTL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKCTL)


# START_BLOCK_FIXTURES
@unittest.skipUnless(shutil.which("git"), "git is required")
class WorkctlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.email", "workctl@example.invalid")
        self.git("config", "user.name", "Workctl Test")
        (self.repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "initial")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True,
            capture_output=True,
            check=True,
        )

    def cli(
        self,
        *args: str,
        expected: int = 0,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            env=merged,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def init_task(self, task_id: str, goal: str = "Continue safely") -> Path:
        self.cli("init", task_id, "--goal", goal)
        return self.repo / ".workctl" / "tasks" / task_id

    def fake_runtime(self, exit_code: int = 0, message: str = "fake runtime complete") -> Path:
        path = Path(self.temporary.name) / f"fake-runtime-{exit_code}.py"
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--version' in sys.argv:\n"
            "    print('fake 1.0')\n"
            "    raise SystemExit(0)\n"
            f"print({message!r})\n"
            f"raise SystemExit({exit_code})\n",
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path

    def configure_runtime(self, name: str, executable: Path) -> None:
        config_path = self.repo / ".workctl" / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["runtimes"][name]["command"] = str(executable)
        config_path.write_text(json.dumps(config), encoding="utf-8")
# END_BLOCK_FIXTURES


# START_BLOCK_TASK_SELECTION
class TaskSelectionTests(WorkctlTestCase):
    def test_explicit_task_is_embedded_in_resume_prompt(self) -> None:
        task = self.init_task("alpha")
        self.cli("handoff", "alpha", "--to", "codex", "--next-action", "Finish parser tests")
        prompts = list((task / "prompts").glob("*-codex.md"))
        self.assertEqual(len(prompts), 1)
        prompt = prompts[0].read_text(encoding="utf-8")
        self.assertIn("CONTINUE TASK alpha ONLY", prompt)
        self.assertIn(str(task / "state.json"), prompt)
        self.assertIn("Do not end your turn merely to report intermediate progress", prompt)
        self.assertIn("locally executable safe next action", prompt)
        self.assertIn("Finish parser tests", (task / "resume.md").read_text(encoding="utf-8"))
        handoff = (task / "handoff.md").read_text(encoding="utf-8")
        self.assertIn("Execution identity evidence", handoff)
        self.assertIn("self_attested", handoff)

    def test_unique_branch_binding_selects_task_and_ambiguity_halts(self) -> None:
        self.init_task("alpha")
        self.git("checkout", "-b", "feature-beta")
        self.init_task("beta")
        self.git("checkout", "-b", "unrelated")
        result = self.cli("resume", expected=2)
        self.assertIn("task is ambiguous", result.stderr)
        self.git("checkout", "main")
        result = self.cli("resume")
        self.assertIn("alpha", result.stdout)

    def test_launch_on_wrong_branch_requires_explicit_bind(self) -> None:
        self.init_task("alpha")
        self.git("checkout", "-b", "other")
        result = self.cli("continue", "alpha", "--runtime", "codex", "--print-command", expected=2)
        self.assertIn("workctl bind alpha", result.stderr)
        self.cli("bind", "alpha")
        result = self.cli("continue", "alpha", "--runtime", "codex", "--print-command")
        self.assertIn("CONTINUE TASK alpha ONLY", result.stdout)

    def test_print_command_does_not_consume_the_next_run_id(self) -> None:
        task = self.init_task("alpha")
        fake = self.fake_runtime()
        self.configure_runtime("claude", fake)
        self.cli("continue", "alpha", "--runtime", "claude", "--print-command")
        self.assertFalse((task / "runs" / "0001").exists())
        self.cli("continue", "alpha", "--runtime", "claude", "--non-interactive")
        self.assertTrue((task / "runs" / "0001" / "post.diff").is_file())
# END_BLOCK_TASK_SELECTION


# START_BLOCK_RUNTIME_RUNS
class RuntimeRunTests(WorkctlTestCase):
    def test_failed_runtime_releases_lease_and_persists_pre_post_snapshots(self) -> None:
        task = self.init_task("alpha")
        fake = self.fake_runtime(exit_code=42)
        self.configure_runtime("claude", fake)
        self.cli("start", "alpha", "--runtime", "claude", "--non-interactive", expected=42)
        state = json.loads((task / "state.json").read_text(encoding="utf-8"))
        self.assertIsNone(state["lease"])
        self.assertEqual(state["runs"][0]["exit_reason"], "failed")
        self.assertEqual(state["runs"][0]["exit_code"], 42)
        run_dir = task / "runs" / "0001"
        self.assertTrue((run_dir / "pre.diff").is_file())
        self.assertTrue((run_dir / "post.diff").is_file())

    def test_limit_message_is_classified_for_noninteractive_runtime(self) -> None:
        task = self.init_task("alpha")
        fake = self.fake_runtime(exit_code=1, message="Usage limit reached; retry later")
        self.configure_runtime("codex", fake)
        self.cli("continue", "alpha", "--runtime", "codex", "--non-interactive", expected=1)
        state = json.loads((task / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["runs"][0]["exit_reason"], "rate_limited")

    def test_live_lease_requires_takeover(self) -> None:
        task = self.init_task("alpha")
        state = json.loads((task / "state.json").read_text(encoding="utf-8"))
        WORKCTL.acquire_lease(task, state, "claude", "0001", takeover=False)
        current = json.loads((task / "state.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(WORKCTL.WorkctlError, "task is leased"):
            WORKCTL.acquire_lease(task, current, "codex", "0002", takeover=False)
        WORKCTL.acquire_lease(task, current, "codex", "0002", takeover=True)
        updated = json.loads((task / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(updated["lease"]["runtime"], "codex")
# END_BLOCK_RUNTIME_RUNS


# START_BLOCK_ROLE_SESSIONS
class RoleSessionTests(WorkctlTestCase):
    def test_reusable_opencode_role_continues_exact_session(self) -> None:
        task = self.init_task("alpha")
        fake = self.fake_runtime()
        self.configure_runtime("opencode", fake)
        self.cli(
            "role-bind",
            "alpha",
            "architect",
            "--runtime",
            "opencode",
            "--session",
            "ses_arch_01",
            "--project-id",
            "project-alpha",
            "--model",
            "provider/model-a",
            "--agent",
            "architect",
            "--variant",
            "high",
        )
        result = self.cli("continue", "alpha", "--role", "architect", "--print-command")
        self.assertIn("--session ses_arch_01", result.stdout)
        self.assertIn("--model provider/model-a", result.stdout)
        self.assertIn("--agent architect", result.stdout)
        self.assertIn("--variant high", result.stdout)
        state = json.loads((task / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["role_sessions"]["architect"]["reuse_policy"], "resume")

    def test_bound_role_rejects_runtime_and_model_drift(self) -> None:
        self.init_task("alpha")
        self.cli(
            "role-bind", "alpha", "coder", "--runtime", "opencode", "--session", "ses_code_01",
            "--model", "provider/model-a",
        )
        result = self.cli(
            "continue", "alpha", "--role", "coder", "--model", "provider/model-b", "--print-command", expected=2
        )
        self.assertIn("model mismatch", result.stderr)
        result = self.cli("continue", "alpha", "--role", "coder", "--runtime", "codex", "--print-command", expected=2)
        self.assertIn("runtime mismatch", result.stderr)

    def test_review_roles_are_fresh_and_cannot_bind_session(self) -> None:
        self.init_task("alpha")
        result = self.cli(
            "role-bind", "alpha", "acceptor", "--runtime", "opencode", "--session", "ses_bad",
            "--model", "provider/model-review", expected=2,
        )
        self.assertIn("fresh-context role", result.stderr)
        self.cli("role-bind", "alpha", "acceptor", "--runtime", "opencode", "--model", "provider/model-review")
        result = self.cli("continue", "alpha", "--role", "acceptor", "--print-command")
        self.assertNotIn("--session", result.stdout)

    def test_cache_and_compaction_telemetry_is_additive(self) -> None:
        task = self.init_task("alpha")
        self.cli(
            "role-bind", "alpha", "coder", "--runtime", "opencode", "--session", "ses_code_01",
            "--model", "provider/model-a",
        )
        self.cli("role-record", "alpha", "coder", "--cache-hit-tokens", "90", "--cache-miss-tokens", "10")
        self.cli("role-record", "alpha", "coder", "--cache-hit-tokens", "10", "--compaction")
        state = json.loads((task / "state.json").read_text(encoding="utf-8"))
        role = state["role_sessions"]["coder"]
        self.assertEqual(role["cache"]["hit_tokens"], 100)
        self.assertEqual(role["cache"]["miss_tokens"], 10)
        self.assertEqual(role["cache"]["compactions"], 1)
        self.assertEqual(role["context_generation"], 2)

    def test_legacy_task_without_role_sessions_remains_readable(self) -> None:
        task = self.init_task("legacy")
        state_path = task / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.pop("role_sessions")
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = self.cli("role-list", "legacy")
        self.assertIn("no role sessions", result.stdout)
        self.cli("status", "legacy")

    def test_archived_role_cannot_continue(self) -> None:
        self.init_task("alpha")
        self.cli(
            "role-bind", "alpha", "architect", "--runtime", "opencode", "--session", "ses_arch_01",
            "--model", "provider/model-a",
        )
        self.cli("role-archive", "alpha", "architect")
        result = self.cli("continue", "alpha", "--role", "architect", "--print-command", expected=2)
        self.assertIn("archived", result.stderr)

    def test_role_state_mutation_respects_task_lease(self) -> None:
        task = self.init_task("alpha")
        self.cli(
            "role-bind", "alpha", "coder", "--runtime", "opencode", "--session", "ses_code_01",
            "--model", "provider/model-a",
        )
        state_path = task / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["lease"] = {
            "runtime": "opencode", "run_id": "0001", "pid": os.getpid(), "acquired_at": "now"
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = self.cli("role-record", "alpha", "coder", "--cache-hit-tokens", "1", expected=2)
        self.assertIn("task is leased", result.stderr)
        result = self.cli("role-archive", "alpha", "coder", expected=2)
        self.assertIn("task is leased", result.stderr)
# END_BLOCK_ROLE_SESSIONS


if __name__ == "__main__":
    unittest.main()
