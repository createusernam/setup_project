# Workctl: One Task Across Multiple Coding CLIs

`workctl` lets a task start in Claude Code, continue in Codex, and later move to OpenCode. It does
not transfer chat history. It transfers durable task state: identity, goal, constraints, decisions,
progress, checks, Git snapshots, and the exact next action.

## Session entry

A fresh CLI/chat session does not automatically load any workctl task.

Inside an already open agent session, resume one task by naming it explicitly:

```text
Continue workctl task <task-id>.
Read its durable state first and report Done / Now / Next before acting.
```

From a normal terminal, launch the target runtime with the same explicit ID:

```bash
workctl continue <task-id> --runtime <runtime>
```

Calling workctl without an ID is safe only when `WORKCTL_TASK` is set, exactly one task is bound to
the current Git branch, or the repository contains exactly one task. Otherwise workctl stops and
requires the task ID; it never guesses by recency.

## Do you need workctl?

Usually, the human should not start with a workctl command.

| What you want | What to say to the agent | Mechanism |
|---|---|---|
| Learn where the project is and what comes next | “What stage are we at, and what should we do next?” | `pipeline-status`; no workctl task is created |
| Continue the current conversation in the same CLI | “Continue the current work” | current agent and project files |
| Continue one named task after a session/provider/CLI switch | “Continue the auth-refresh task in Codex” | `workctl` |
| Choose among several active tasks | “Show the active tasks” | read-only workctl status, then the human names one |

The agent should translate these requests into the underlying checks. You only need a terminal
command when launching a different CLI, because one interactive coding CLI must not start another
inside itself. At that point the agent should give exactly one launch action, not the whole command
catalog.

## Why it exists

Session history belongs to one CLI and model. A repository may contain several active tasks, so a
generic instruction such as “continue the work” is ambiguous. Durable task files remain the source
of truth; a reusable model session is an optional cache resource, not a replacement for them.
`workctl` gives each task an explicit address:

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

## Terminal reference: first cross-CLI task

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

Generated handoffs disclose execution identity separately from configured intent. Workctl records
the launcher runtime/model/session when it controls the run; this is `launcher_recorded`, not proof
that the provider actually served that identity. Link provider-issued identity evidence in
`checks.json` when available. Otherwise the handoff labels the actual runtime/model identity
`self_attested` so final acceptance never mistakes configuration for independent provenance.

That prompt also carries a persistence condition: an intermediate progress report does not end the
task. The runtime keeps taking safe, locally executable next actions in the same turn until the task
contract is complete, a real authority/external-state blocker is reached, or the provider forces an
exit. If an agent repeatedly stops while its own next action is executable, that is an execution-loop
failure; do not treat repeated human “continue” messages as the normal workctl protocol.

## Persistent role sessions

For repeated work in OpenCode, bind a named role to an existing session instead of starting from an
empty context on every iteration:

```bash
workctl role-bind auth-refresh coder \
  --runtime opencode \
  --session ses_abc123 \
  --model provider/model-id \
  --agent build \
  --variant high
workctl continue auth-refresh --runtime opencode --role coder
```

The binding is exact: task, repository, runtime, session ID, model, agent, and variant are checked
before launch. Runtime or model drift stops execution. `role-list` shows active bindings;
`role-archive` rotates one deliberately. A task lease still guarantees one controller for the task,
including all of its role sessions.

Review and acceptance roles are fresh-context roles. Bind them with `--fresh`; `workctl` rejects a
reusable session for `review_test`, `review_acceptance`, `reviewer`, `evaluator`, or `acceptor`.
Session reuse improves prefix-cache affinity but does not satisfy reviewer independence.

Record provider telemetry when available:

```bash
workctl role-record auth-refresh coder --cache-hit-tokens 95000 --cache-miss-tokens 5000
workctl role-record auth-refresh coder --compaction
```

Counters are additive. Compaction increments the context generation; it does not erase durable task
state. Archive and bind a new session when context quality degrades, the model/runtime changes, the
role changes, or an independent review begins.

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
workctl role-list auth-refresh           # show persistent/fresh role bindings
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

Not transferred between runtimes:

- hidden model context;
- an internal reasoning trace;
- full chat history.

Continuation quality therefore depends on current task files and correct links to pipeline
artifacts. A same-runtime role binding may resume one provider session, but that affinity is local
to the declared runtime/model and remains subordinate to the durable artifacts.

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
