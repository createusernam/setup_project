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
is_frontend: null
is_architecturally_complex: null
grace_mode: "pending"   # set from the selected route after discovery and planning
```

## Commands

```bash
dev:   pending
build: pending
test:  pending
```

## Pipeline

See `~/setup/docs/human/PIPELINE.md` for full process.

Key reminders:
1. Fill all 9 neutral brief sections using your preferred discovery process; maintain `evidence-handoff.json`
2. GRACE Lite mandatory — MODULE_CONTRACT in every file
3. All agent outputs follow structured JSON format (see `~/setup/docs/agent/PROMPT-FORMAT.md`)
4. Judge before shipping any feature
5. Route skills before tools: load a named or clearly matching skill. `planning-with-files` is
   mandatory for a saved-and-executed plan, likely 5+ tool calls, or cross-CLI/provider continuity.
6. Discovery: Claude reads `~/.claude/skills/`; Codex reads `~/.agents/skills/`; OpenCode scans
   both. Setup links both roots to the same canonical skill source.

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

For material work, use one named workctl task (`workctl init <task-id> --goal "..."`). Its
`.workctl/tasks/<task-id>/` directory owns Done/Now/Next, checks, and runtime handoff. Never infer the
task by recency when several tasks exist.

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
