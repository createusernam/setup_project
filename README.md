# Setup v2 — Development Harness

A cross-model development harness: a canonical pipeline (Phase -1 → 7) that takes a
`product_brief.md` from idea to shipped code through structured, verifiable state files —
GRACE markup, product-brief-driven design, and LLM-as-judge verification at every gate.
Works with Claude Code, OpenCode + DeepSeek, or any terminal LLM as the orchestrator.

**Core philosophy**: LLMs don't read docs — they follow trajectories set by structured context.
This setup encodes that into every artifact and prompt.

Three consequences, load-bearing throughout:

- **The graph comes first, then contracts, then code.** Skip the explicit graph and the model builds
  its own from fragments, freezes it in KV-cache, and defends it. GRACE Full is on by default.
- **The handoff to a cheap model is code, not a spec.** `/scaffold` (Phase 5.5) writes marked-up
  skeletons — contracts, named blocks, log anchors, `IMPL:` directives, no logic. A spec costs about
  what the code costs to write, and a small model imitates code far more faithfully than prose.
- **Rules that aren't checked don't exist.** GRACE Lite is enforced by `scripts/grace-lint.sh`, not by
  asking nicely; `verify.method: trace` grades the execution trajectory, not just return values.

---

## Install

**Claude Code:**
```bash
git clone https://github.com/createusernam/setup_project.git ~/setup
bash ~/setup/install.sh
```
Verify: open Claude Code, type `/startup` — should appear in the skill list.

**OpenCode:** same clone + `install.sh` (skills are read from the same `~/.claude/skills/`
path), then add the `instructions` + `mcp.playwright` block to
`~/.config/opencode/opencode.json`. Full snippet: `docs/human/SETUP.md`.

**Any terminal LLM:** clone the repo, paste a `SKILL.md`'s content into your prompt — you are
the orchestrator.

## First project

After `/startup <name>`, choose exactly one Phase -1 producer:

1. run `/methodology` and let it discover and write `product_brief.md`; or
2. fill all 9 brief sections manually.

Use `/researcher` only for remaining factual gaps, then run `/judge product-brief` and
`/grill-with-docs`. GRACE Lite is mandatory in source files; GRACE Full planning is enabled by
default and has only a documented small-change opt-out. The canonical sequence and gates live in
[`docs/human/PIPELINE.md`](docs/human/PIPELINE.md).

---

## Directory structure

```
setup/
├── README.md              # this file — what it is + how to find things
├── AGENTS.md               # global agent rules (OpenCode entrypoint)
├── model-routing.json      # phase → model, requires, human_gate (read by preflight)
├── install.sh
├── docs/
│   ├── human/  PIPELINE.md · SETUP.md · ARCHITECTURE-GUIDE.md · WORKCTL.md
│   └── agent/  PROMPT-FORMAT.md · COMPAT.md
├── scripts/                # model-check · preflight · GRACE lint · runtime-aware skill validation
├── skills/                 # one dir per skill — symlinked into ~/.claude/skills/
├── agents/                 # evaluator.md · team.md
└── templates/project/      # copied into new projects by /startup
```

`install.sh` symlinks every skill and exposes `scripts/` at `~/.claude/scripts/`, so skills can call
the gates from any project directory:

```bash
bash ~/.claude/scripts/pipeline-preflight.sh 6   # inputs present · models routed · human gate signed
bash ~/.claude/scripts/grace-lint.sh --changed   # GRACE Lite markup on the diff
bash ~/.claude/scripts/model-check.sh 5.5        # which model this phase requires
python3 ~/setup/scripts/validate-skills.py --profile claude  # validate Claude skill frontmatter
workctl doctor                                                # check cross-CLI task continuation
```

**Install is fail-closed on collisions.** If a skill already exists in `~/.claude/skills/` as a real
directory (not a symlink into this repo), install halts instead of skipping it. A skipped skill is the
worst failure mode there is: you edit the skill here, commit it, and the CLI keeps loading a stale copy
from somewhere else — silently, for weeks.

---

## Where to go next

- **Human workflow, step by step** (install → new project → first session → each pipeline
  phase): [`docs/human/PIPELINE.md`](docs/human/PIPELINE.md)
- **Install / troubleshooting reference**: [`docs/human/SETUP.md`](docs/human/SETUP.md)
- **Architecture phase** (reasoning-hard design on a clean prompt): [`docs/human/ARCHITECTURE-GUIDE.md`](docs/human/ARCHITECTURE-GUIDE.md)
- **Continue one named task across coding CLIs**: [`docs/human/WORKCTL.md`](docs/human/WORKCTL.md)
- **Agent-facing standards** (structured prompts, cross-model compat, model routing):
  [`docs/agent/PROMPT-FORMAT.md`](docs/agent/PROMPT-FORMAT.md), [`docs/agent/COMPAT.md`](docs/agent/COMPAT.md)
- **Global agent rules** (OpenCode/Claude Code entrypoint): [`AGENTS.md`](AGENTS.md)

## Attribution

The `grace-*` skills are adapted from [osovv/grace-marketplace](https://github.com/osovv/grace-marketplace)
(MIT). Full notice: [`NOTICE.md`](NOTICE.md).

## Relationship to claude-config

This repo extends, does not replace, `claude-config` (personal config, agents, global skills).
Install both — see `docs/human/SETUP.md`.
