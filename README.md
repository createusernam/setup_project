# Setup v2 — Development Harness

A cross-model development harness: a canonical pipeline (Phase -1 → 7) that takes a
`product_brief.md` from idea to shipped code through structured, verifiable state files —
GRACE markup, product-brief-driven design, and independent machine, model, reviewer, and human gates.
Works with Claude Code, Codex, OpenCode, or any terminal/API LLM as the orchestrator.

## Install

The installer is supported on Linux and Windows through WSL2. Native Windows and macOS are not
currently validated install targets; the artifact/skill fallback remains portable. See
[`docs/human/SETUP.md`](docs/human/SETUP.md) for the support matrix and exact installation steps.

**Claude Code:**
```bash
git clone https://github.com/createusernam/setup_project.git ~/setup
bash ~/setup/install.sh
```
Verify: open Claude Code, type `/startup` — should appear in the skill list.

**Codex and OpenCode:** use the same clone + `install.sh`. The installer links one canonical skill
tree into both standard discovery roots and installs the same routing policy for every CLI. For
OpenCode, then add the `instructions` + `mcp.playwright` block to
`~/.config/opencode/opencode.json`. Full snippet: `docs/human/SETUP.md`.

**Any terminal LLM:** clone the repo, paste a `SKILL.md`'s content into your prompt — you are
the orchestrator.

## First project

After `/startup <name>`, configure `model-bindings.json` and continue with the operator loop in
[`docs/human/PIPELINE.md`](docs/human/PIPELINE.md). If a task may move between coding CLIs, create
its explicit identity with `workctl init <task-id> --goal "..."`; workctl does not replace pipeline
phases or gates.

---

## Directory structure

```
setup/
├── README.md              # this file — what it is + how to find things
├── AGENTS.md               # global agent rules (OpenCode entrypoint)
├── pipeline-machine.json   # phase → semantic transition, risk policy, invalidation
├── model-routing.json      # phase → capability profiles and collegium policy
├── install.sh
├── docs/
│   ├── human/  PIPELINE.md · SETUP.md · ARCHITECTURE-GUIDE.md · WORKCTL.md
│   └── agent/  PROMPT-FORMAT.md · COMPAT.md · SKILL-ROUTING.md
├── scripts/                # model-check · preflight · GRACE lint · skill discovery/validation
├── skills/                 # canonical skills → ~/.claude/skills and ~/.agents/skills
├── agents/                 # evaluator.md · team.md
└── templates/project/      # copied into new projects by /startup
```

`install.sh` symlinks every skill and exposes `scripts/` at `~/.claude/scripts/`, so skills can call
the gates from any project directory:

```bash
bash ~/.claude/scripts/pipeline-preflight.sh 6   # risk policy · semantic outcomes · attestations · models · human gate
bash ~/.claude/scripts/grace-lint.sh --changed   # GRACE Lite markup on the diff
bash ~/.claude/scripts/model-check.sh 5.5 .      # resolve the project's configured model binding
python3 ~/setup/scripts/validate-skills.py --profile claude  # validate Claude skill frontmatter
workctl doctor                                                # check cross-CLI task continuation
setup-skill-doctor                                            # check discovery + routing in every CLI
```

Model routing is provider-neutral: phases require capability profiles, while each project maps
those profiles to concrete runtime/model IDs in `model-bindings.json`. Allowed field values and a
complete example are in [`docs/agent/COMPAT.md`](docs/agent/COMPAT.md); the copied
`model-bindings.schema.json` is the machine-readable contract.

**Install is fail-closed on collisions.** It preflights both discovery roots before changing either.
If a stale copy exists, the default run halts without partial installation. Re-run with
`--migrate-skill-collisions` to move conflicts into a timestamped backup and link the canonical
source; old copies are never deleted.

---

## Where to go next

| I need to… | Start here |
|---|---|
| install, select a CLI, create/adopt a project, or configure a model | [`SETUP.md`](docs/human/SETUP.md) |
| select a risk tier, run/resume a phase, pass a gate, or register evidence | [`PIPELINE.md`](docs/human/PIPELINE.md) |
| hand an architecture decision back into the pipeline | [`ARCHITECTURE-GUIDE.md`](docs/human/ARCHITECTURE-GUIDE.md) |
| continue one named task in another coding CLI | [`WORKCTL.md`](docs/human/WORKCTL.md) |
| change a machine-facing contract or learn allowed config values | [`COMPAT.md`](docs/agent/COMPAT.md) and the adjacent JSON schema |

`SETUP.md` owns installation and project configuration. `PIPELINE.md` owns phase operation and
gate state; do not look for a second operator runbook.

## Attribution

The `grace-*` skills are adapted from [osovv/grace-marketplace](https://github.com/osovv/grace-marketplace)
(MIT). Full notice: [`NOTICE.md`](NOTICE.md).

## Relationship to claude-config

This repo extends, does not replace, `claude-config` (personal config, agents, global skills).
Install both — see `docs/human/SETUP.md`.
