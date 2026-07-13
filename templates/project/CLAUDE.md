# PROJECT_NAME

<!-- Fill this file when running /startup. Keep ≤ 200 lines. -->

## Stack

- Frontend: REPLACE (or "none")
- Backend: REPLACE (or "none")
- Database: REPLACE (or "none")
- Key dependencies: REPLACE

## Config

```yaml
is_frontend: false
is_architecturally_complex: false
grace_mode: "lite"   # lite (always) | full (if ≥2/4 criteria)
```

## Commands

```bash
dev:   REPLACE
build: REPLACE
test:  REPLACE
```

## Pipeline

See `~/setup/docs/human/PIPELINE.md` for full process.

Key reminders:
1. Fill `product_brief.md` before anything else
2. GRACE Lite mandatory — MODULE_CONTRACT in every file
3. All agent outputs follow structured JSON format (see `~/setup/docs/agent/PROMPT-FORMAT.md`)
4. Judge before shipping any feature
5. OpenCode: this file is read via `AGENTS.md` symlink. Skills discovered from `~/.claude/skills/`.

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

## Continuity & memory (cross-session)

Long / multi-session work: keep `CONTINUITY.md` (copy from `CONTINUITY_TEMPLATE.md`) updated after each milestone — it survives `/compact`. Memory is **bounded & curated** — no unbounded session-log:

| Need | Lives in |
|------|----------|
| Why decisions were made | `docs/adr/` |
| What happened per session | `CHANGELOG.md` |
| Where we are now | `CONTINUITY.md` |
| Known bugs | GitHub issues |

## GitHub

Repo: REPLACE_WITH_REPO_URL
Issues: REPLACE_WITH_ISSUES_URL

## Domain context

See `docs/agents/domain.md` for terminology and domain context.
