# PROJECT_NAME

<!-- Fill this file when running /startup. Keep ≤ 200 lines. -->

## Stack

- Status: deferred until architecture planning
- Frontend: unknown
- Backend: unknown
- Database: unknown
- Key dependencies: unknown

## Config

```yaml
is_frontend: null                 # null until discovery; then true | false
is_architecturally_complex: null  # null until route selection; then true | false
grace_mode: "pending"             # pending | lite | full; derive from selected route
```

## Commands

```bash
dev:   pending
build: pending
test:  pending
```

## Pipeline

See `~/setup/docs/human/PIPELINE.md` for full process.

When the user asks what stage the project is at, what comes next, where work stopped, or to continue,
in any language, use the `pipeline-status` skill. Read `.pipeline-state.json` and run the current
preflight plus its bound phase-process validator behind the scenes; never infer phase from chat history. Answer with the stage,
readiness/blockers, and one next action. The human does not need to remember pipeline commands.

Key reminders:
1. Fill all 9 neutral brief sections using your preferred discovery process; maintain `evidence-handoff.json`
2. GRACE Lite mandatory — MODULE_CONTRACT in every file
3. All agent outputs follow structured JSON format (see `~/setup/docs/agent/PROMPT-FORMAT.md`)
4. Judge before shipping any feature
5. Route skills before tools: load a named or clearly matching skill. `planning-with-files` is
   mandatory for a saved-and-executed plan, likely 5+ tool calls, or cross-CLI/provider continuity.
6. Discovery: Claude reads `~/.claude/skills/`; Codex reads `~/.agents/skills/`; OpenCode scans
   both. Setup links both roots to the same canonical skill source.
7. Enter phases atomically with `setup-pipeline enter PHASE`, then run
   `setup-pipeline guard PHASE` before the first phase-owned write. Never use mutation-first phase
   switching or hand-edit the ledger.
8. Every skill exit runs `setup-pipeline status` and returns `continue_now`,
   `waiting_for_human`, or `complete`. Continue machine-owned work immediately; at a human boundary
   reproduce the complete HumanRequest printed by status: authority, one question, why, resolvable
   evidence/instruction paths, exact file+schema or inline response format, allowed responses,
   consequences, and resume action. Never replace it with an underspecified chat question or wait
   for the human to ask what comes next.
9. Core preflight applies to every phase. If a selected skill owns additional durable state, bind
   its trusted validator once with `setup-pipeline set-process PHASE SKILL`. A validator failure
   overrides READY. Every declared phase output must remain a checked downstream input.

## GRACE Lite (mandatory)

Every file starts with:

```
// FILE: path/to/file.ext
// START_MODULE_CONTRACT
//   PURPOSE: [one sentence]
//   SCOPE: [what operations]
//   DEPENDS: [or "none"]
// END_MODULE_CONTRACT
```

## Continuity & memory (cross-session and cross-CLI)

For material work that must cross a CLI/session boundary or coexist with other active tasks, use one
named workctl task (`workctl init <task-id> --goal "..."`). Its
`.workctl/tasks/<task-id>/` directory owns Done/Now/Next, checks, and runtime handoff. Never infer the
task by recency when several tasks exist.

`pipeline-status` answers where the project is in the delivery pipeline. `workctl` answers where one
named implementation task is. Report them separately; a project-status question does not require
creating a workctl task.

`CONTINUITY.md` is a manual fallback only when workctl is unavailable. Do not maintain both for the
same task: two current-state ledgers will drift. Memory stays **bounded & curated**:

| Need | Lives in |
|------|----------|
| Why decisions were made | `docs/adr/` |
| What happened per session | `CHANGELOG.md` |
| Pipeline phase and gates | `.pipeline-state.json` |
| Where a named task is now | `.workctl/tasks/<task-id>/progress.md` (or fallback `CONTINUITY.md`) |
| Known bugs | GitHub issues |

## GitHub

Repo: REPLACE_WITH_REPO_URL
Issues: REPLACE_WITH_ISSUES_URL

## Domain context

See `docs/agents/domain.md` for terminology and domain context.
