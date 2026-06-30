# Setup v2 — Development Harness

Private repo (`createusernam/setup`). Full methodology included.

## Key files

- `README.md` — entry point, install instructions for Claude Code / OpenCode / terminal
- `SETUP.md` — manual install steps, GRACE setup, troubleshooting
- `PIPELINE.md` — canonical 9-phase process (Phase -1 to Phase 7)
- `COMPAT.md` — cross-model/CLI compatibility: Claude Code, OpenCode+DeepSeek, terminal
- `PROMPT-FORMAT.md` — structured prompt standard (PCAM, Belief State, metamodel check)
- `GRACE-ONTOLOGY.md` — GRACE annotation vocabulary and business grounding
- `METHODOLOGY.md` — encapsulation rules for private МК-methodology integration
- `publish-public.sh` — sync script to public `createusernam/setup_project`

## Skills

All skills in `skills/` → symlinked to `~/.claude/skills/` by `install.sh`:

| Skill | Purpose |
|-------|---------|
| `startup` | Create new project from template |
| `researcher` | Multi-agent research flow (market, domain, technical, mk) |
| `judge` | LLM-as-Judge artifact evaluation |
| `design-first` | Wireframe → API contract for frontend |
| `methodology` | МК product discovery v3 (private) |

## Templates

`templates/project/` — copied to new projects by `/startup`.

## Per-project init (OpenCode)

```
1. /startup my-project-name       # creates ~/my-project/
2. cd ~/my-project
3. ln -sf CLAUDE.md AGENTS.md     # OpenCode reads AGENTS.md
```

Full pipeline: `PIPELINE.md`. Model routing: `COMPAT.md`.
