# Workctl: One Task Across Multiple Coding CLIs

`workctl` lets a task start in Claude Code, continue in Codex, and later move to OpenCode. It does
not transfer chat history. It transfers durable task state: identity, goal, constraints, decisions,
progress, checks, Git snapshots, and the exact next action.

## Why it exists

Session history belongs to one CLI and model. A repository may contain several active tasks, so a
generic instruction such as “continue the work” is ambiguous. `workctl` gives each task an explicit
address:

```text
.workctl/tasks/auth-refresh/
├── state.json       # task ID, branch, revision, integrity
├── context.md       # goal, constraints, links to pipeline artifacts
├── contract.json    # task-level completion criteria and exclusions
├── plan.md          # current execution phase and steps
├── decisions.md     # accepted and rejected decisions
├── progress.md      # done, now, next, blockers
├── checks.json      # checks and actual results
├── handoff.md       # concise transfer to the next runtime
├── resume.md        # generated continuation prompt
└── runs/            # Git snapshots, logs, and launch prompts
```

State stays beside the code and does not depend on one provider remaining available.

## Relationship to the pipeline

`workctl` is not a pipeline phase and does not replace skills or gates:

- `.pipeline-state.json` owns the current phase and gate state;
- root artifacts such as `product_brief.md`, `task_plan.md`, and `contract.json` define approved
  intent and completion requirements;
- `.workctl/tasks/<task-id>/` owns one task's identity, Done/Now/Next, decisions, checks, Git
  snapshots, and runtime history.

Link to current pipeline artifacts from task `context.md`; do not copy them into a competing spec.
Task-local `plan.md` covers near-term execution, and task-local `contract.json` covers that task's
criteria. If they conflict with a root phase artifact, the phase artifact wins and the task summary
must be updated.

Do not maintain `CONTINUITY.md` for the same task. It would become a second current-state ledger.

## Quick start

```bash
bash ~/setup/install.sh
cd ~/work/my-project
workctl doctor
workctl init auth-refresh --goal "Update the authentication flow"
workctl start auth-refresh --runtime claude
```

Before implementation, add links to pipeline artifacts in `context.md` and refine task-level
criteria in `contract.json`. During work, keep `plan.md`, `decisions.md`, `progress.md`, and
`checks.json` current. These files are operational memory for the next agent, not ceremonial reports.

`workctl start` and `workctl continue` launch child CLIs. Run them from a normal terminal, not from
inside an existing interactive Claude, Codex, or OpenCode session.

When a provider limit is reached:

```bash
workctl handoff auth-refresh --to codex
workctl continue auth-refresh --runtime codex
```

The same task may later move again:

```bash
workctl handoff auth-refresh --to opencode
workctl continue auth-refresh --runtime opencode
```

The receiving runtime gets an explicit `CONTINUE TASK auth-refresh ONLY` prompt, absolute paths to
task material, and an instruction to read state before acting. Each launch records pre/post Git
snapshots and exit information under `runs/` and `state.json`.

## Selecting among multiple tasks

Use the task ID explicitly:

```bash
workctl status
workctl continue auth-refresh --runtime codex
workctl continue billing-webhooks --runtime opencode
```

Without an ID, selection is allowed only when unambiguous:

1. `WORKCTL_TASK` is set;
2. exactly one task is bound to the current Git branch; or
3. the repository contains exactly one task.

With multiple candidates, `workctl` stops. It does not choose the most recently modified task and
does not keep one global “active task” pointer that could conflict across terminals.

For repeated commands in one terminal:

```bash
export WORKCTL_TASK=auth-refresh
workctl continue --runtime codex
```

## Branches and parallel work

`init` binds a task to the current Git branch. Launch is blocked after switching branches so an
agent cannot write task changes into the wrong branch.

If moving the task to the current branch is intentional:

```bash
workctl bind auth-refresh
```

One process controls a task at a time. After a crashed CLI, `--takeover` can remove a stale lease,
but first inspect the recorded process:

```bash
workctl status auth-refresh --json
workctl continue auth-refresh --runtime codex --takeover
```

For real parallel implementation, use separate tasks and branches or worktrees. Do not run two
agents against one task state.

## Useful commands

```bash
workctl status                           # list tasks and safe selection information
workctl status auth-refresh --json       # machine-readable status
workctl handoff auth-refresh --to codex  # update handoff.md and resume.md
workctl resume auth-refresh              # print the continuation prompt without launching
workctl runs auth-refresh                # show launch history
workctl doctor                           # check Claude, Codex, and OpenCode availability
workctl continue auth-refresh --runtime codex --print-command
```

Runtime commands live in `.workctl/config.json`. OpenCode configuration may pin a provider/model and
agent name; other runtimes may pin a model and launch flags.

## What transfers

Transferred:

- task identity and goal;
- constraints and artifact links;
- accepted/rejected decisions;
- code/Git state;
- checks and actual results;
- known uncertainty, risks, and blockers;
- exact next action and runtime history.

Not transferred:

- hidden model context;
- an internal reasoning trace;
- full chat history.

Continuation quality therefore depends on current task files and correct links to pipeline
artifacts.

`workctl` does not automatically switch providers after an interactive launch. Coding CLIs do not
expose one reliable cross-runtime signal for “provider limit reached.” An explicit
`continue ... --runtime ...` keeps authority transfer visible. In non-interactive mode, common
rate-limit messages may be classified diagnostically; this is not automatic delegation.

## Good handoff protocol

Before leaving a runtime, record:

- concrete current state rather than “almost done”;
- the next executable action;
- modified and uncommitted files;
- verification commands and actual results;
- decisions that cannot be recovered from code alone;
- known uncertainty, risks, and blockers.

Then run `workctl handoff <task-id> --to <runtime>`. The next runtime begins by reading task state
and checking the working tree, not by guessing from a one-line prompt.
