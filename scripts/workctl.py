#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Continue one materialized task safely across Claude Code, Codex, and OpenCode runtimes.
# SCOPE: Manage project-local task state, task selection, leases, git checkpoints, handoffs, resume prompts, and CLI launches.
# DEPENDS: Python standard library, optional git repository, and installed runtime CLIs selected by the user.
# END_MODULE_CONTRACT
"""Cross-runtime task continuation for the setup development harness."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
from typing import Any


# START_BLOCK_CONTRACTS
SCHEMA_VERSION = 1
TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
CANONICAL_ARTIFACTS = (
    "context.md",
    "plan.md",
    "contract.json",
    "decisions.md",
    "progress.md",
    "handoff.md",
    "checks.json",
)
RUNTIME_NAMES = ("claude", "codex", "opencode")
FRESH_CONTEXT_ROLES = {
    "acceptor",
    "evaluator",
    "reviewer",
    "review_acceptance",
    "review_test",
    "test_owner",
}
LIMIT_PATTERNS = (
    "rate limit",
    "usage limit",
    "quota exceeded",
    "too many requests",
    "limit reached",
    "insufficient credits",
)


class WorkctlError(RuntimeError):
    """Expected user-facing failure that should not produce a traceback."""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkctlError(f"missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkctlError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkctlError(f"expected a JSON object in {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
# END_BLOCK_CONTRACTS


# START_BLOCK_WORKSPACE
def git_output(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def discover_repo(explicit: str | None) -> Path:
    candidate = Path(explicit or os.getcwd()).expanduser().resolve()
    root = git_output(candidate, "rev-parse", "--show-toplevel")
    return Path(root).resolve() if root else candidate


def control_root(repo: Path) -> Path:
    return repo / ".workctl"


def tasks_root(repo: Path) -> Path:
    return control_root(repo) / "tasks"


def task_dir(repo: Path, task_id: str) -> Path:
    validate_task_id(task_id)
    return tasks_root(repo) / task_id


def validate_task_id(task_id: str) -> None:
    if not TASK_ID.fullmatch(task_id):
        raise WorkctlError("task id must be 1-64 letters, digits, dots, underscores, or hyphens")


def list_task_ids(repo: Path) -> list[str]:
    root = tasks_root(repo)
    if not root.is_dir():
        return []
    return sorted(path.name for path in root.iterdir() if (path / "state.json").is_file())


def load_state(repo: Path, task_id: str) -> tuple[Path, dict[str, Any]]:
    directory = task_dir(repo, task_id)
    state = read_json(directory / "state.json")
    if state.get("schema_version") != SCHEMA_VERSION:
        raise WorkctlError(
            f"unsupported state schema {state.get('schema_version')!r} for {task_id}; expected {SCHEMA_VERSION}"
        )
    if state.get("task_id") != task_id:
        raise WorkctlError(f"state task_id mismatch in {directory / 'state.json'}")
    return directory, state


def current_branch(repo: Path) -> str | None:
    return git_output(repo, "branch", "--show-current") or None


def resolve_task(repo: Path, supplied: str | None) -> str:
    if supplied:
        load_state(repo, supplied)
        return supplied
    from_env = os.environ.get("WORKCTL_TASK", "").strip()
    if from_env:
        load_state(repo, from_env)
        return from_env

    task_ids = list_task_ids(repo)
    if not task_ids:
        raise WorkctlError("no tasks found; run `workctl init <task-id> --goal ...`")
    branch = current_branch(repo)
    if branch:
        matches = []
        for task_id in task_ids:
            _, state = load_state(repo, task_id)
            if state.get("workspace", {}).get("branch") == branch:
                matches.append(task_id)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise WorkctlError(
                f"multiple tasks are bound to branch {branch!r}: {', '.join(matches)}; pass TASK-ID explicitly"
            )
    if len(task_ids) == 1:
        return task_ids[0]
    raise WorkctlError(
        "task is ambiguous; pass TASK-ID or set WORKCTL_TASK. Candidates: " + ", ".join(task_ids)
    )


def artifact_hashes(directory: Path) -> dict[str, str]:
    return {
        name: sha256_file(directory / name)
        for name in CANONICAL_ARTIFACTS
        if (directory / name).is_file()
    }


def artifact_drift(directory: Path, state: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    previous = state.get("artifacts", {})
    current = artifact_hashes(directory)
    drift: dict[str, dict[str, str | None]] = {}
    for name in sorted(set(previous) | set(current)):
        if previous.get(name) != current.get(name):
            drift[name] = {"recorded": previous.get(name), "current": current.get(name)}
    return drift


def workspace_mismatch(repo: Path, state: dict[str, Any]) -> str | None:
    workspace = state.get("workspace", {})
    expected_repo = workspace.get("repo_path")
    if expected_repo and Path(expected_repo).resolve() != repo.resolve():
        return f"task is bound to repository {expected_repo!r}, current repository is {str(repo)!r}"
    expected = workspace.get("branch")
    actual = current_branch(repo)
    if expected and actual and expected != actual:
        return f"task is bound to branch {expected!r}, current branch is {actual!r}"
    return None


def require_matching_workspace(repo: Path, state: dict[str, Any], task_id: str) -> None:
    mismatch = workspace_mismatch(repo, state)
    if mismatch:
        raise WorkctlError(f"{mismatch}; run `workctl bind {task_id}` only if this move is intentional")
# END_BLOCK_WORKSPACE


# START_BLOCK_CONFIG_AND_RUNTIME
def default_config() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "runtimes": {
            "claude": {"command": "claude", "model": None},
            "codex": {"command": "codex", "model": None, "sandbox": "workspace-write"},
            "opencode": {"command": "opencode", "model": None, "agent": None, "variant": None},
        },
    }


def load_config(repo: Path) -> dict[str, Any]:
    config = default_config()
    path = control_root(repo) / "config.json"
    if not path.exists():
        return config
    raw = read_json(path)
    if raw.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise WorkctlError(f"unsupported config schema in {path}")
    runtimes = raw.get("runtimes", {})
    if not isinstance(runtimes, dict):
        raise WorkctlError(f"runtimes must be an object in {path}")
    for name, override in runtimes.items():
        if name not in config["runtimes"] or not isinstance(override, dict):
            raise WorkctlError(f"invalid runtime config for {name!r} in {path}")
        config["runtimes"][name].update(override)
    return config


def runtime_settings(repo: Path, runtime: str, model: str | None) -> dict[str, Any]:
    if runtime not in RUNTIME_NAMES:
        raise WorkctlError(f"unknown runtime {runtime!r}; choose from {', '.join(RUNTIME_NAMES)}")
    settings = dict(load_config(repo)["runtimes"][runtime])
    if model:
        settings["model"] = model
    command = settings.get("command")
    if not isinstance(command, str) or not command.strip():
        raise WorkctlError(f"runtime {runtime!r} has no executable command")
    return settings


def build_runtime_command(
    runtime: str,
    settings: dict[str, Any],
    repo: Path,
    prompt: str,
    non_interactive: bool,
    output_path: Path,
) -> list[str]:
    command = settings["command"]
    model = settings.get("model")
    if runtime == "claude":
        args = [command]
        if non_interactive:
            args.append("-p")
        if model:
            args.extend(["--model", str(model)])
        args.append(prompt)
        return args
    if runtime == "codex":
        sandbox = str(settings.get("sandbox") or "workspace-write")
        args = [command]
        if non_interactive:
            args.append("exec")
        args.extend(["-C", str(repo), "-s", sandbox])
        if model:
            args.extend(["--model", str(model)])
        if non_interactive:
            args.extend(["--output-last-message", str(output_path)])
        args.append(prompt)
        return args
    args = [command]
    if non_interactive:
        args.extend(["run", "--dir", str(repo), "--format", "json"])
    else:
        args.extend([str(repo), "--prompt"])
    if model:
        args.extend(["--model", str(model)])
    if settings.get("agent"):
        args.extend(["--agent", str(settings["agent"])])
    if settings.get("variant"):
        args.extend(["--variant", str(settings["variant"])])
    if settings.get("session_id"):
        args.extend(["--session", str(settings["session_id"])])
    args.append(prompt)
    return args


def probe_runtime(name: str, settings: dict[str, Any]) -> dict[str, Any]:
    command = settings["command"]
    resolved = shutil.which(command) if os.sep not in command else command
    if not resolved or not Path(resolved).exists():
        return {"available": False, "detail": "not found", "command": command}
    try:
        result = subprocess.run(
            [resolved, "--version"],
            text=True,
            capture_output=True,
            timeout=4,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"available": False, "detail": "version probe timed out", "command": resolved}
    except OSError as exc:
        return {"available": False, "detail": str(exc), "command": resolved}
    detail = (result.stdout or result.stderr).strip().splitlines()
    return {
        "available": result.returncode == 0,
        "detail": detail[0] if detail else f"exit {result.returncode}",
        "command": resolved,
    }
# END_BLOCK_CONFIG_AND_RUNTIME


# START_BLOCK_CHECKPOINTS_AND_LEASES
def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def live_lease(state: dict[str, Any]) -> dict[str, Any] | None:
    lease = state.get("lease")
    if not isinstance(lease, dict):
        return None
    return lease if pid_alive(lease.get("pid")) else None


def require_unleased(state: dict[str, Any], action: str) -> None:
    active = live_lease(state)
    if active:
        raise WorkctlError(
            f"cannot {action} while task is leased by {active.get('runtime')} pid={active.get('pid')}"
        )


def acquire_lease(
    directory: Path,
    state: dict[str, Any],
    runtime: str,
    run_id: str,
    takeover: bool,
) -> None:
    active = live_lease(state)
    if active and not takeover:
        raise WorkctlError(
            f"task is leased by {active.get('runtime')} pid={active.get('pid')} since {active.get('acquired_at')}; "
            "use --takeover only after confirming that process should be superseded"
        )
    state["lease"] = {
        "runtime": runtime,
        "run_id": run_id,
        "pid": os.getpid(),
        "acquired_at": now_iso(),
        "takeover_of": active,
    }
    save_state(directory, state, bump=True)


def release_lease(directory: Path, state: dict[str, Any], run_id: str) -> None:
    lease = state.get("lease")
    if isinstance(lease, dict) and lease.get("run_id") == run_id:
        state["lease"] = None
        save_state(directory, state, bump=True)


def git_snapshot(repo: Path, run_dir: Path, label: str) -> dict[str, Any]:
    branch = current_branch(repo)
    head = git_output(repo, "rev-parse", "HEAD")
    pathspec = ("--", ".", ":(exclude).workctl/**")
    status = git_output(repo, "status", "--short", *pathspec)
    diff = git_output(repo, "diff", "--binary", "HEAD", *pathspec) if head else None
    diff_path = run_dir / f"{label}.diff"
    atomic_write(diff_path, (diff or "") + ("\n" if diff else ""))
    return {
        "captured_at": now_iso(),
        "branch": branch,
        "head": head,
        "status": status or "",
        "diff": str(diff_path),
        "diff_sha256": sha256_file(diff_path),
    }


def save_state(directory: Path, state: dict[str, Any], bump: bool) -> None:
    if bump:
        state["revision"] = int(state.get("revision", 0)) + 1
    state["updated_at"] = now_iso()
    state["artifacts"] = artifact_hashes(directory)
    write_json(directory / "state.json", state)


def next_run_id(state: dict[str, Any]) -> str:
    return f"{len(state.get('runs', [])) + 1:04d}"


def classify_exit(code: int, captured: str) -> str:
    lowered = captured.lower()
    if any(pattern in lowered for pattern in LIMIT_PATTERNS):
        return "rate_limited"
    if code in (130, -signal.SIGINT):
        return "user_exit"
    return "exited" if code == 0 else "failed"
# END_BLOCK_CHECKPOINTS_AND_LEASES


# START_BLOCK_PROMPTS
def render_resume(
    directory: Path,
    state: dict[str, Any],
    runtime: str,
    drift: dict[str, Any],
    snapshot: dict[str, Any],
    role: str | None = None,
) -> str:
    files = [name for name in CANONICAL_ARTIFACTS if (directory / name).exists()]
    handoff = (directory / "handoff.md").read_text(encoding="utf-8") if (directory / "handoff.md").exists() else "No authored handoff is available; reconstruct from state and git evidence."
    drift_lines = "\n".join(f"- {name}" for name in drift) or "- none"
    file_lines = "\n".join(f"- `{directory / name}`" for name in files)
    return f"""# Resume task {state['task_id']}

## Runtime

- target runtime: `{runtime}`
- role: `{role or 'portable-handoff'}`
- task revision: `{state.get('revision')}`
- repository: `{state.get('workspace', {}).get('repo_path')}`
- branch at checkpoint: `{snapshot.get('branch')}`
- HEAD at checkpoint: `{snapshot.get('head')}`

## Canonical files

{file_lines}

## Artifact drift since last saved state

{drift_lines}

## Current git status

```text
{snapshot.get('status') or '(clean)'}
```

## Recorded next action

{state.get('next_action') or 'Inspect the task artifacts and determine the smallest safe next action.'}

## Latest handoff

{handoff}
"""


def render_agent_prompt(directory: Path, state: dict[str, Any], runtime: str, resume_path: Path, role: str | None = None) -> str:
    return f"""CONTINUE TASK {state['task_id']} ONLY.

You are taking over an existing task from another coding CLI. Do not choose a different task from nearby files and do not restart this task from scratch.

Repository: {state.get('workspace', {}).get('repo_path')}
Task state: {directory / 'state.json'}
Resume package: {resume_path}
Current revision: {state.get('revision')}
Assigned role: {role or 'portable handoff'}

Before changing files:
1. Read the resume package and every canonical file it lists.
2. Inspect the current git status and diff. Preserve all existing user and prior-agent changes; never reset or discard them.
3. Confirm that the recorded branch and task id match this workspace.
4. Continue from the recorded next action, adjusting it only when repository evidence requires it.

During work, keep `{directory / 'progress.md'}` and `{directory / 'decisions.md'}` current. Before intentionally switching runtimes, run `workctl handoff {state['task_id']} --to <runtime> --next-action "..."`. If you cannot complete the task, leave observable files and checks in a resumable state.

Do not end your turn merely to report intermediate progress. While a locally executable safe next action remains, continue the tool/work loop in this same turn. Stop only when the task contract is complete, a genuine authority/external-state blocker prevents further progress, or the runtime/provider forces an exit. A progress update is not a terminal condition.

Target runtime for this handoff: {runtime}.
"""


def prepare_resume(repo: Path, directory: Path, state: dict[str, Any], runtime: str, role: str | None = None) -> tuple[Path, str]:
    drift = artifact_drift(directory, state)
    recovery_dir = directory / "runs" / "recovery"
    snapshot = git_snapshot(repo, recovery_dir, f"resume-r{state.get('revision', 0)}")
    resume_text = render_resume(directory, state, runtime, drift, snapshot, role)
    resume_path = directory / "resume.md"
    atomic_write(resume_path, resume_text)
    prompt = render_agent_prompt(directory, state, runtime, resume_path, role)
    role_suffix = f"-{role}" if role else ""
    prompt_path = directory / "prompts" / f"resume-r{state.get('revision', 0)}-{runtime}{role_suffix}.md"
    atomic_write(prompt_path, prompt)
    return prompt_path, prompt
# END_BLOCK_PROMPTS


# START_BLOCK_COMMANDS
def command_init(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    validate_task_id(args.task_id)
    directory = task_dir(repo, args.task_id)
    if directory.exists():
        raise WorkctlError(f"task already exists: {directory}")
    directory.mkdir(parents=True)
    (directory / "runs").mkdir()
    (directory / "prompts").mkdir()
    control_root(repo).mkdir(exist_ok=True)
    config_path = control_root(repo) / "config.json"
    if not config_path.exists():
        write_json(config_path, default_config())

    branch = current_branch(repo)
    head = git_output(repo, "rev-parse", "HEAD")
    created = now_iso()
    atomic_write(
        directory / "context.md",
        f"# Task {args.task_id}\n\n## Goal\n\n{args.goal}\n\n## Repository\n\n`{repo}`\n",
    )
    atomic_write(
        directory / "plan.md",
        f"# Plan: {args.task_id}\n\n## Current phase\n\nDefine the smallest safe next step.\n\n## Steps\n\n- [ ] Confirm scope and acceptance criteria\n",
    )
    write_json(
        directory / "contract.json",
        {
            "goal": args.goal,
            "acceptance_criteria": [],
            "constraints": [],
            "out_of_scope": [],
        },
    )
    atomic_write(directory / "decisions.md", f"# Decisions: {args.task_id}\n\n")
    atomic_write(directory / "progress.md", f"# Progress: {args.task_id}\n\n- {created}: task initialized\n")
    write_json(directory / "checks.json", {"updated_at": None, "checks": []})
    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": args.task_id,
        "goal": args.goal,
        "stage": "active",
        "revision": 0,
        "created_at": created,
        "updated_at": created,
        "workspace": {
            "repo_path": str(repo),
            "branch": branch,
            "initial_head": head,
        },
        "next_action": args.next_action or "Inspect context.md and create or confirm the plan.",
        "last_runtime": None,
        "target_runtime": None,
        "lease": None,
        "runs": [],
        "role_sessions": {},
        "artifacts": {},
    }
    save_state(directory, state, bump=True)
    print(f"Created task {args.task_id}: {directory}")
    print(f"Branch binding: {branch or '(not a git repository)'}")
    print(f"Next: complete context.md and contract.json, then run `workctl start {args.task_id} --runtime claude`")
    return 0


def task_summary(repo: Path, task_id: str) -> dict[str, Any]:
    directory, state = load_state(repo, task_id)
    lease = live_lease(state)
    return {
        "task": task_id,
        "revision": state.get("revision"),
        "stage": state.get("stage"),
        "branch": state.get("workspace", {}).get("branch"),
        "last_runtime": state.get("last_runtime"),
        "target_runtime": state.get("target_runtime"),
        "role_sessions": sorted(state.get("role_sessions", {})) if isinstance(state.get("role_sessions", {}), dict) else [],
        "lease": f"{lease.get('runtime')} pid={lease.get('pid')}" if lease else None,
        "next_action": state.get("next_action"),
        "drift": sorted(artifact_drift(directory, state)),
        "workspace_mismatch": workspace_mismatch(repo, state),
    }


def command_status(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    if args.task_id:
        summaries = [task_summary(repo, resolve_task(repo, args.task_id))]
    else:
        task_ids = list_task_ids(repo)
        if not task_ids:
            print("No workctl tasks.")
            return 0
        summaries = [task_summary(repo, task_id) for task_id in task_ids]
    if args.json:
        print(json.dumps(summaries[0] if len(summaries) == 1 else summaries, indent=2, ensure_ascii=False))
        return 0
    for item in summaries:
        print(f"{item['task']}  stage={item['stage']}  rev={item['revision']}  branch={item['branch'] or '-'}")
        print(f"  runtime={item['last_runtime'] or '-'}  target={item['target_runtime'] or '-'}  lease={item['lease'] or '-'}")
        print(f"  role sessions: {', '.join(item['role_sessions']) or '-'}")
        print(f"  next: {item['next_action']}")
        if item["drift"]:
            print(f"  artifact drift: {', '.join(item['drift'])}")
        if item["workspace_mismatch"]:
            print(f"  BLOCKED: {item['workspace_mismatch']}")
    return 0


def command_bind(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    directory, state = load_state(repo, args.task_id)
    active = live_lease(state)
    if active:
        raise WorkctlError(
            f"cannot rebind while {active.get('runtime')} pid={active.get('pid')} holds the task lease"
        )
    branch = current_branch(repo)
    if not branch:
        raise WorkctlError("cannot bind task because the current workspace has no git branch")
    previous = state.get("workspace", {}).get("branch")
    state.setdefault("workspace", {})["repo_path"] = str(repo)
    state["workspace"]["branch"] = branch
    save_state(directory, state, bump=True)
    print(f"Bound {args.task_id}: {previous or '-'} → {branch}")
    return 0


def validate_role(role: str) -> None:
    if not TASK_ID.fullmatch(role):
        raise WorkctlError("role must be 1-64 letters, digits, dots, underscores, or hyphens")


def get_role_session(state: dict[str, Any], role: str) -> dict[str, Any]:
    validate_role(role)
    sessions = state.get("role_sessions", {})
    if not isinstance(sessions, dict):
        raise WorkctlError("role_sessions in task state must be an object")
    record = sessions.get(role)
    if not isinstance(record, dict):
        raise WorkctlError(f"role {role!r} is not bound; run `workctl role-bind <task> {role} ...`")
    if record.get("status") != "active":
        raise WorkctlError(f"role {role!r} session is {record.get('status')!r}; bind a new session before continuing")
    return record


def command_role_bind(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    directory, state = load_state(repo, args.task_id)
    require_matching_workspace(repo, state, args.task_id)
    validate_role(args.role)
    require_unleased(state, "bind a role")
    settings = runtime_settings(repo, args.runtime, args.model)
    model = settings.get("model")
    fresh = args.fresh or args.role in FRESH_CONTEXT_ROLES
    if fresh and args.session:
        raise WorkctlError(f"fresh-context role {args.role!r} cannot bind a reusable session ID")
    if not fresh:
        if args.runtime != "opencode":
            raise WorkctlError("reusable role sessions are currently supported only for the OpenCode runtime")
        if not args.session:
            raise WorkctlError("reusable role session requires --session")
        if not model:
            raise WorkctlError("reusable role session requires an explicit --model or configured runtime model")
    created = now_iso()
    sessions = state.setdefault("role_sessions", {})
    if not isinstance(sessions, dict):
        raise WorkctlError("role_sessions in task state must be an object")
    previous = sessions.get(args.role)
    context_generation = int(previous.get("context_generation", 0)) + 1 if isinstance(previous, dict) else 1
    sessions[args.role] = {
        "runtime": args.runtime,
        "session_id": None if fresh else args.session,
        "project_id": args.project_id,
        "repo_path": str(repo),
        "model_id": model,
        "agent": args.agent or settings.get("agent") or args.role,
        "variant": args.variant or settings.get("variant"),
        "title": args.title or f"{args.task_id}-{args.role}",
        "reuse_policy": "fresh" if fresh else "resume",
        "created_at": created,
        "last_used_at": None,
        "context_generation": context_generation,
        "cache": {
            "hit_tokens": 0,
            "miss_tokens": 0,
            "last_hit_ratio": None,
            "compactions": 0,
            "updated_at": None,
        },
        "status": "active",
    }
    save_state(directory, state, bump=True)
    print(
        f"Bound role {args.role} for {args.task_id}: runtime={args.runtime} "
        f"policy={sessions[args.role]['reuse_policy']} session={sessions[args.role]['session_id'] or '-'}"
    )
    return 0


def command_role_list(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    task_id = resolve_task(repo, args.task_id)
    _, state = load_state(repo, task_id)
    sessions = state.get("role_sessions", {})
    if not isinstance(sessions, dict):
        raise WorkctlError("role_sessions in task state must be an object")
    if args.json:
        print(json.dumps(sessions, indent=2, ensure_ascii=False))
        return 0
    if not sessions:
        print(f"{task_id}: no role sessions bound")
        return 0
    for role, record in sorted(sessions.items()):
        print(
            f"{role}  status={record.get('status')}  policy={record.get('reuse_policy')}  "
            f"runtime={record.get('runtime')}  model={record.get('model_id') or '-'}  "
            f"session={record.get('session_id') or '-'}"
        )
    return 0


def command_role_archive(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    directory, state = load_state(repo, args.task_id)
    require_matching_workspace(repo, state, args.task_id)
    require_unleased(state, "archive a role")
    record = get_role_session(state, args.role)
    record["status"] = "archived"
    record["archived_at"] = now_iso()
    save_state(directory, state, bump=True)
    print(f"Archived role session {args.task_id}/{args.role}")
    return 0


def command_role_record(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    directory, state = load_state(repo, args.task_id)
    require_matching_workspace(repo, state, args.task_id)
    require_unleased(state, "record role telemetry")
    record = get_role_session(state, args.role)
    cache = record.setdefault("cache", {})
    if not isinstance(cache, dict):
        raise WorkctlError("role cache telemetry must be an object")
    hit = int(args.cache_hit_tokens or 0)
    miss = int(args.cache_miss_tokens or 0)
    if hit < 0 or miss < 0:
        raise WorkctlError("cache token increments must be non-negative")
    cache["hit_tokens"] = int(cache.get("hit_tokens", 0)) + hit
    cache["miss_tokens"] = int(cache.get("miss_tokens", 0)) + miss
    total = cache["hit_tokens"] + cache["miss_tokens"]
    cache["last_hit_ratio"] = cache["hit_tokens"] / total if total else None
    if args.compaction:
        cache["compactions"] = int(cache.get("compactions", 0)) + 1
        record["context_generation"] = int(record.get("context_generation", 1)) + 1
    cache["updated_at"] = now_iso()
    save_state(directory, state, bump=True)
    print(
        f"Recorded {args.task_id}/{args.role}: hit={cache['hit_tokens']} miss={cache['miss_tokens']} "
        f"ratio={cache['last_hit_ratio']} compactions={cache.get('compactions', 0)}"
    )
    return 0


def command_handoff(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    task_id = resolve_task(repo, args.task_id)
    directory, state = load_state(repo, task_id)
    require_matching_workspace(repo, state, task_id)
    if args.to not in RUNTIME_NAMES:
        raise WorkctlError(f"unknown target runtime {args.to!r}")
    run_dir = directory / "runs" / "handoffs"
    snapshot = git_snapshot(repo, run_dir, f"handoff-r{state.get('revision', 0)}")
    runs = state.get("runs", []) if isinstance(state.get("runs", []), list) else []
    last_run = runs[-1] if runs and isinstance(runs[-1], dict) else {}
    identity_source = "launcher_recorded" if last_run else "self_attested"
    identity_runtime = last_run.get("runtime") or state.get("last_runtime") or "unknown"
    identity_model = last_run.get("model") or "unknown"
    identity_session = last_run.get("session_id") or "not-recorded"
    text = f"""# Handoff: {task_id}

## Generated

{now_iso()}

## From / to

- previous runtime: `{state.get('last_runtime') or 'unknown'}`
- target runtime: `{args.to}`
- task revision before handoff: `{state.get('revision')}`

## Execution identity evidence

- source: `{identity_source}`
- runtime: `{identity_runtime}`
- configured model: `{identity_model}`
- runtime session: `{identity_session}`
- actual runtime/model identity: `self_attested` unless a provider-issued evidence artifact is linked in `checks.json`

## What was completed

{args.completed or 'Reconstruct completed work from progress.md and the current diff.'}

## What remains

{args.remaining or 'Continue from the recorded next action.'}

## Risks and open questions

{args.risks or 'See decisions.md, plan.md, and current repository evidence.'}

## Required checks

- Review `{snapshot['diff']}` and current `git status` before editing.
- Re-run checks affected by any interrupted command.
- Do not reset or discard the existing working tree.

## Next action

{args.next_action or state.get('next_action')}
"""
    atomic_write(directory / "handoff.md", text)
    state["target_runtime"] = args.to
    state["next_action"] = args.next_action or state.get("next_action")
    state["lease"] = None
    save_state(directory, state, bump=True)
    prompt_path, _ = prepare_resume(repo, directory, state, args.to)
    save_state(directory, state, bump=False)
    print(f"Handoff {task_id} → {args.to}")
    print(f"Resume prompt: {prompt_path}")
    print(f"Continue: workctl continue {task_id} --runtime {args.to}")
    return 0


def command_resume(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    task_id = resolve_task(repo, args.task_id)
    directory, state = load_state(repo, task_id)
    require_matching_workspace(repo, state, task_id)
    runtime = args.runtime or state.get("target_runtime") or state.get("last_runtime") or "claude"
    prompt_path, prompt = prepare_resume(repo, directory, state, runtime)
    print(prompt if args.print_prompt else f"Resume prompt: {prompt_path}")
    return 0


def command_runs(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    task_id = resolve_task(repo, args.task_id)
    _, state = load_state(repo, task_id)
    runs = state.get("runs", [])
    if args.json:
        print(json.dumps(runs, indent=2, ensure_ascii=False))
        return 0
    if not runs:
        print(f"{task_id}: no runtime runs recorded")
        return 0
    for run in runs:
        print(
            f"{run.get('id')}  {run.get('runtime')}  model={run.get('model') or '-'}  "
            f"exit={run.get('exit_reason') or 'active'}  code={run.get('exit_code')}"
        )
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    repo = discover_repo(args.repo)
    config = load_config(repo)
    failed = False
    for name in RUNTIME_NAMES:
        result = probe_runtime(name, config["runtimes"][name])
        mark = "OK" if result["available"] else "FAIL"
        print(f"{mark:4} {name:8} {result['detail']} ({result['command']})")
        failed = failed or not result["available"]
    return 1 if failed else 0


def command_launch(args: argparse.Namespace, mode: str) -> int:
    repo = discover_repo(args.repo)
    task_id = resolve_task(repo, args.task_id)
    directory, state = load_state(repo, task_id)
    require_matching_workspace(repo, state, task_id)
    role = args.role
    role_record: dict[str, Any] | None = None
    if role:
        role_record = get_role_session(state, role)
        expected_repo = role_record.get("repo_path")
        if expected_repo and Path(expected_repo).resolve() != repo.resolve():
            raise WorkctlError(f"role {role!r} is bound to repository {expected_repo!r}; rotate or rebind it")
        role_runtime = role_record.get("runtime")
        if args.runtime and args.runtime != role_runtime:
            raise WorkctlError(f"role {role!r} runtime mismatch: bound {role_runtime!r}, requested {args.runtime!r}")
        runtime = str(role_runtime)
        role_model = role_record.get("model_id")
        if args.model and args.model != role_model:
            raise WorkctlError(f"role {role!r} model mismatch: bound {role_model!r}, requested {args.model!r}")
        settings = runtime_settings(repo, runtime, str(role_model) if role_model else None)
        settings["agent"] = role_record.get("agent")
        settings["variant"] = role_record.get("variant")
        if role_record.get("reuse_policy") == "resume":
            if runtime != "opencode" or not role_record.get("session_id"):
                raise WorkctlError(f"role {role!r} has an invalid reusable session binding; rotate or rebind it")
            settings["session_id"] = role_record["session_id"]
    else:
        runtime = args.runtime or state.get("target_runtime") or "claude"
        settings = runtime_settings(repo, runtime, args.model)
    prompt_path, prompt = prepare_resume(repo, directory, state, runtime, role)
    run_id = next_run_id(state)
    run_dir = directory / "runs" / run_id
    output_path = run_dir / "last-message.txt"
    command = build_runtime_command(runtime, settings, repo, prompt, args.non_interactive, output_path)
    if args.print_command:
        print(shlex.join(command))
        print(f"Prompt file: {prompt_path}")
        return 0

    probe = probe_runtime(runtime, settings)
    if not probe["available"] and not args.skip_probe:
        raise WorkctlError(
            f"runtime {runtime} is unavailable: {probe['detail']}; fix `.workctl/config.json` or use --skip-probe"
        )
    run_dir.mkdir(parents=True, exist_ok=False)
    acquire_lease(directory, state, runtime, run_id, args.takeover)
    state = read_json(directory / "state.json")
    pre = git_snapshot(repo, run_dir, "pre")
    record: dict[str, Any] = {
        "id": run_id,
        "mode": mode,
        "runtime": runtime,
        "role": role,
        "model": settings.get("model"),
        "session_id": settings.get("session_id"),
        "variant": settings.get("variant"),
        "started_at": now_iso(),
        "ended_at": None,
        "command": command,
        "prompt": str(prompt_path),
        "pre": pre,
        "post": None,
        "exit_code": None,
        "exit_reason": None,
    }
    state.setdefault("runs", []).append(record)
    state["last_runtime"] = runtime
    state["target_runtime"] = None
    save_state(directory, state, bump=True)
    print(f"Starting {runtime} for task {task_id} (run {run_id})")
    if role:
        print(f"Role: {role} ({role_record.get('reuse_policy')})")
    print(f"Task root: {directory}")

    captured = ""
    code = 1
    try:
        if args.non_interactive:
            log_path = run_dir / "runtime.log"
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    command,
                    cwd=repo,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                state = read_json(directory / "state.json")
                state["lease"]["pid"] = process.pid
                save_state(directory, state, bump=False)
                assert process.stdout is not None
                for line in process.stdout:
                    sys.stdout.write(line)
                    log.write(f"[Workctl][command_run][STREAM] {line}")
                    captured = (captured + line)[-65536:]
                code = process.wait()
        else:
            process = subprocess.Popen(command, cwd=repo)
            state = read_json(directory / "state.json")
            state["lease"]["pid"] = process.pid
            save_state(directory, state, bump=False)
            code = process.wait()
    except KeyboardInterrupt:
        code = 130
        try:
            process.terminate()
        except (NameError, ProcessLookupError):
            pass
    except OSError as exc:
        captured = str(exc)
        code = 127
        print(f"workctl: runtime launch failed: {exc}", file=sys.stderr)
    finally:
        state = read_json(directory / "state.json")
        post = git_snapshot(repo, run_dir, "post")
        for item in state.get("runs", []):
            if item.get("id") == run_id:
                item["ended_at"] = now_iso()
                item["post"] = post
                item["exit_code"] = code
                item["exit_reason"] = classify_exit(code, captured)
                break
        state["last_runtime"] = runtime
        if role:
            current_role = state.get("role_sessions", {}).get(role, {})
            if isinstance(current_role, dict):
                current_role["last_used_at"] = now_iso()
        save_state(directory, state, bump=True)
        release_lease(directory, state, run_id)
    print(f"Run {run_id} ended: {classify_exit(code, captured)} (exit {code})")
    print(f"Continue elsewhere: workctl continue {task_id} --runtime <claude|codex|opencode>")
    return code
# END_BLOCK_COMMANDS


# START_BLOCK_CLI
def add_repo_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", help="repository/workspace path; defaults to current git root")


def add_task_argument(parser: argparse.ArgumentParser, required: bool = False) -> None:
    parser.add_argument("task_id", nargs=None if required else "?", help="task id; otherwise resolve safely")


def add_launch_arguments(parser: argparse.ArgumentParser) -> None:
    add_task_argument(parser)
    add_repo_argument(parser)
    parser.add_argument("--runtime", choices=RUNTIME_NAMES)
    parser.add_argument("--model", help="runtime-specific model id; OpenCode expects provider/model")
    parser.add_argument("--role", help="bound role session to use; reusable sessions stay task- and role-specific")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--print-command", action="store_true", help="prepare and print without launching")
    parser.add_argument("--takeover", action="store_true", help="supersede a confirmed live lease")
    parser.add_argument("--skip-probe", action="store_true", help="launch even if bounded version probe fails")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workctl", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="materialize a new portable task")
    add_task_argument(init, required=True)
    add_repo_argument(init)
    init.add_argument("--goal", required=True)
    init.add_argument("--next-action")
    init.set_defaults(handler=command_init)

    status = sub.add_parser("status", help="list tasks or inspect one task")
    add_task_argument(status)
    add_repo_argument(status)
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=command_status)

    bind = sub.add_parser("bind", help="explicitly bind a task to the current branch/workspace")
    add_task_argument(bind, required=True)
    add_repo_argument(bind)
    bind.set_defaults(handler=command_bind)

    role_bind = sub.add_parser("role-bind", help="bind a persistent or fresh-context runtime role")
    add_task_argument(role_bind, required=True)
    role_bind.add_argument("role")
    add_repo_argument(role_bind)
    role_bind.add_argument("--runtime", required=True, choices=RUNTIME_NAMES)
    role_bind.add_argument("--session", help="OpenCode session ID; forbidden for fresh-context roles")
    role_bind.add_argument("--project-id", help="optional runtime-native project identifier for audit")
    role_bind.add_argument("--model", help="exact runtime model ID")
    role_bind.add_argument("--agent", help="runtime agent name; defaults to the role name")
    role_bind.add_argument("--variant", help="provider/runtime-specific effort variant")
    role_bind.add_argument("--title", help="stable human-readable session title")
    role_bind.add_argument("--fresh", action="store_true", help="force a fresh context on every launch")
    role_bind.set_defaults(handler=command_role_bind)

    role_list = sub.add_parser("role-list", help="list role-session bindings for a task")
    add_task_argument(role_list)
    add_repo_argument(role_list)
    role_list.add_argument("--json", action="store_true")
    role_list.set_defaults(handler=command_role_list)

    role_archive = sub.add_parser("role-archive", help="archive one role-session binding")
    add_task_argument(role_archive, required=True)
    role_archive.add_argument("role")
    add_repo_argument(role_archive)
    role_archive.set_defaults(handler=command_role_archive)

    role_record = sub.add_parser("role-record", help="record cache/compaction telemetry for a role")
    add_task_argument(role_record, required=True)
    role_record.add_argument("role")
    add_repo_argument(role_record)
    role_record.add_argument("--cache-hit-tokens", type=int, default=0)
    role_record.add_argument("--cache-miss-tokens", type=int, default=0)
    role_record.add_argument("--compaction", action="store_true")
    role_record.set_defaults(handler=command_role_record)

    handoff = sub.add_parser("handoff", help="checkpoint and target another runtime")
    add_task_argument(handoff)
    add_repo_argument(handoff)
    handoff.add_argument("--to", required=True, choices=RUNTIME_NAMES)
    handoff.add_argument("--completed")
    handoff.add_argument("--remaining")
    handoff.add_argument("--risks")
    handoff.add_argument("--next-action")
    handoff.set_defaults(handler=command_handoff)

    resume = sub.add_parser("resume", help="regenerate a runtime-specific resume package")
    add_task_argument(resume)
    add_repo_argument(resume)
    resume.add_argument("--runtime", choices=RUNTIME_NAMES)
    resume.add_argument("--print-prompt", action="store_true")
    resume.set_defaults(handler=command_resume)

    runs = sub.add_parser("runs", help="show runtime provenance and exits")
    add_task_argument(runs)
    add_repo_argument(runs)
    runs.add_argument("--json", action="store_true")
    runs.set_defaults(handler=command_runs)

    doctor = sub.add_parser("doctor", help="bounded availability probes for all runtimes")
    add_repo_argument(doctor)
    doctor.set_defaults(handler=command_doctor)

    start = sub.add_parser("start", help="launch the first or next runtime for a task")
    add_launch_arguments(start)
    start.set_defaults(handler=lambda args: command_launch(args, "start"))

    cont = sub.add_parser("continue", help="continue an existing task in another runtime")
    add_launch_arguments(cont)
    cont.set_defaults(handler=lambda args: command_launch(args, "continue"))
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return int(args.handler(args))
    except WorkctlError as exc:
        print(f"workctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
