# Setup v2 — Development Harness

A cross-model development harness: a canonical pipeline (Phase -1 → 7) that takes a
`product_brief.md` from idea to shipped code through structured, verifiable state files —
GRACE markup, product-brief-driven design, and LLM-as-judge verification at every gate.
Works with Claude Code, OpenCode + DeepSeek, or any terminal LLM as the orchestrator.

**Core philosophy**: LLMs don't read docs — they follow trajectories set by structured context.
This setup encodes that into every artifact and prompt.

---

## Install

**Claude Code:**
```bash
git clone https://github.com/createusernam/setup_project.git ~/.setup
bash ~/.setup/install.sh
```
Verify: open Claude Code, type `/startup` — should appear in the skill list.

**OpenCode:** same clone + `install.sh` (skills are read from the same `~/.claude/skills/`
path), then add the `instructions` + `mcp.playwright` block to
`~/.config/opencode/opencode.json`. Full snippet: `docs/human/SETUP.md`.

**Any terminal LLM:** clone the repo, paste a `SKILL.md`'s content into your prompt — you are
the orchestrator.

---

## Directory structure

```
setup/
├── README.md              # this file — what it is + how to find things
├── AGENTS.md               # global agent rules (OpenCode entrypoint)
├── model-routing.json      # phase → model, requires, human_gate (read by preflight)
├── install.sh
├── docs/
│   ├── human/  PIPELINE.md · SETUP.md · ARCHITECTURE-GUIDE.md
│   └── agent/  PROMPT-FORMAT.md · COMPAT.md
├── scripts/                # model-check.sh · pipeline-preflight.sh
├── skills/                 # one dir per skill
├── agents/                 # evaluator.md · team.md
└── templates/project/      # copied into new projects by /startup
```

---

## Where to go next

- **Human workflow, step by step** (install → new project → first session → each pipeline
  phase): [`docs/human/PIPELINE.md`](docs/human/PIPELINE.md)
- **Install / troubleshooting reference**: [`docs/human/SETUP.md`](docs/human/SETUP.md)
- **Architecture phase** (reasoning-hard design on a clean prompt): [`docs/human/ARCHITECTURE-GUIDE.md`](docs/human/ARCHITECTURE-GUIDE.md)
- **Agent-facing standards** (structured prompts, cross-model compat, model routing):
  [`docs/agent/PROMPT-FORMAT.md`](docs/agent/PROMPT-FORMAT.md), [`docs/agent/COMPAT.md`](docs/agent/COMPAT.md)
- **Global agent rules** (OpenCode/Claude Code entrypoint): [`AGENTS.md`](AGENTS.md)

## Relationship to claude-config

This repo extends, does not replace, `claude-config` (personal config, agents, global skills).
Install both — see `docs/human/SETUP.md`.
