---
name: workctl
description: Continue one specific coding task safely across Claude Code, Codex, and OpenCode. Use when the user switches CLI, reaches a provider limit, asks for a handoff or resume prompt, returns to a repository containing multiple active tasks, or needs durable task state independent of chat history.
---

# Workctl

Use `workctl` as the task-level control plane when a conversation may move between coding CLIs. Repository phase artifacts remain canonical for specification and gates; `.workctl/tasks/<task-id>/` is canonical for task identity, current execution state, and runtime provenance. A reusable model session is an optional cache resource, never the source of truth.

## Conversational contract

Do not make the human operate workctl for normal project orientation. If they ask where the project
is or what comes next, use `pipeline-status`. Use workctl only when one concrete task must survive a
CLI/session/provider switch, when several tasks coexist, or when the user names a task to resume.

In an agent conversation, translate requests such as “continue auth-refresh in Codex” or “where is
the auth-refresh task?” into read-only inspection first. Explain the task's Done/Now/Next and only
then perform or propose the exact handoff. `start` and `continue` launch child CLIs, so do not run
them inside an interactive coding CLI; tell the human the one terminal action needed at that point.
Do not dump the full command catalog unless asked.

When the setup pipeline is present, do not copy or redefine root `product_brief.md`, `task_plan.md`,
`contract.json`, or other phase outputs inside the task files. Reference their paths from
`context.md`; if a summary conflicts with a phase artifact, the phase artifact wins and the task
summary must be corrected. `.pipeline-state.json` owns phase/gate truth. Do not maintain
`CONTINUITY.md` alongside a workctl-managed task.

The task-local `plan.md` is only the near-term execution plan; task-local `contract.json` contains
acceptance criteria for this named unit of work. Neither replaces the root PBS plan or build
contract. Run `start` and `continue` from a controlling terminal because they launch a child CLI;
do not nest them inside another interactive coding CLI.

## Non-negotiable rule

Continue exactly one identified task. Never infer “the latest task” from prose, timestamps, or a model session when several tasks exist.

Task resolution is deliberately strict:

1. Explicit task ID supplied to the command.
2. `WORKCTL_TASK` environment variable.
3. The only task bound to the current Git branch.
4. The sole task in the repository.

If resolution is ambiguous, stop and show `workctl status`. Require the user or calling agent to name the task. Do not create or edit a global “active task” pointer.

## Workflow

### Create durable task state

From the target repository:

```bash
workctl init auth-refresh --goal "Refresh authentication flow"
```

Fill the generated task files as work progresses:

- `context.md`: scope, constraints, relevant files, and user intent.
- `contract.json`: machine-readable goal, acceptance criteria, constraints, and exclusions.
- `plan.md`: current phase and executable steps.
- `decisions.md`: decisions and rejected alternatives with reasons.
- `progress.md`: completed, current, next, and blocked work.
- `checks.json`: commands run and their results.

Keep those files useful to a fresh agent. Do not rely on chat-only context.

### Start or continue in a runtime

```bash
workctl start auth-refresh --runtime claude
workctl continue auth-refresh --runtime codex
workctl continue auth-refresh --runtime opencode
```

`start` and `continue` both build a task-specific prompt, capture pre/post Git checkpoints, record run provenance, and hold a task lease while the child CLI runs. The prompt begins with `CONTINUE TASK <id> ONLY` and names the canonical files by absolute path.

For iterative OpenCode work, bind a stable role to an existing provider session:

```bash
workctl role-bind auth-refresh coder --runtime opencode \
  --session ses_abc123 --model provider/model-id --agent build --variant high
workctl continue auth-refresh --runtime opencode --role coder
```

The task, repository, runtime, session, model, agent, and variant form one exact binding. Stop on
runtime/model drift. Use `role-list` to inspect bindings and `role-archive` before deliberate
rotation. The task lease remains the single-writer boundary across every role.

Reviewer roles (`review_test`, `review_acceptance`, `reviewer`, `evaluator`, `acceptor`) require
fresh context and reject reusable sessions. Bind them with `--fresh`. Session reuse is a cache
optimization; it never proves reviewer independence.

When the provider exposes token-cache data, append it with `role-record`. A compaction increments
the role's context generation but does not replace the task artifacts. Rotate a role when its model,
runtime, responsibility, or context quality changes.

When a runtime limit is reached, update the durable task files if possible, exit that CLI, then run `workctl continue <id> --runtime <next-runtime>`. Interactive CLIs do not expose a portable “quota exhausted” exit reason, so do not silently chain into another provider.

Use `--non-interactive` only when unattended execution is intended. It can classify common rate-limit output, but it gives the agent authority to run without an interactive checkpoint.

### Hand off without launching

```bash
workctl handoff auth-refresh --to codex
workctl resume auth-refresh
```

`handoff` refreshes the human-readable handoff and resume prompt. `resume` prints the prompt for manual paste or inspection.

### Resolve branch or lease conflicts

Changing a task's branch is explicit:

```bash
workctl bind auth-refresh
```

Do this only after confirming that the checked-out branch is where the task should continue. A branch mismatch is a safety failure, not a warning.

If a previous CLI crashed, inspect the recorded PID before taking over:

```bash
workctl continue auth-refresh --runtime codex --takeover
```

Use `--takeover` only when the recorded process is gone or the user intentionally wants a second controller to replace it.

## Inspection and diagnostics

```bash
workctl status
workctl status auth-refresh --json
workctl runs auth-refresh
workctl role-list auth-refresh
workctl doctor
workctl continue auth-refresh --runtime codex --print-command
```

Before continuing, read at minimum `state.json`, `context.md`, `contract.json`, `plan.md`, `decisions.md`, `progress.md`, `checks.json`, and the generated resume prompt. Then inspect the working tree and verify any claims in `checks.json` that matter to the next action.

## Completion discipline

Before declaring the task complete:

1. Update `progress.md` with the actual terminal state and remaining work.
2. Record relevant verification in `checks.json`.
3. Record decisions that another runtime would otherwise have to rediscover.
4. If another runtime will continue, run `workctl handoff <task-id> --to <runtime>`; do not invent a
   target merely to mark completion.
5. Report the explicit task ID and verification result to the user.

Do not treat a successful CLI exit as proof that the task is complete.
