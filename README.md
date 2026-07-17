# Setup v2 — Development Harness

A cross-model development harness: a canonical pipeline (Phase -1 → 7) that takes a
`product_brief.md` from idea to shipped code through structured, verifiable state files —
GRACE markup, product-brief-driven design, and independent machine, model, reviewer, and human gates.
Works with Claude Code, Codex, OpenCode, or any terminal/API LLM as the orchestrator.

## Start here

There are two runbooks and no duplicated command path:

1. **Install or update the harness:** follow [`SETUP.md`](docs/human/SETUP.md). It is the only
   source of truth for supported platforms, installation, runtime-specific configuration, and
   verification.
2. **Create or deliver a project:** follow the ordered human checklist in
   [`PIPELINE.md`](docs/human/PIPELINE.md). It is the only source of truth for phase order, optional
   branches, gates, and acceptance.

This README is orientation only. Do not copy operational commands into it; update the owning
runbook instead.

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
└── templates/project/      # copied into new projects by the startup skill
```

`install.sh` exposes the shared skills and runtime-neutral operator commands from one canonical
source. Their installation, verification, and allowed inputs belong to `SETUP.md` and
`PIPELINE.md`, not this orientation page.

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
| install the harness, select/configure a CLI, or add an optional browser evaluator | [`SETUP.md`](docs/human/SETUP.md) |
| create/adopt a project, configure its route/models, run a phase, pass a gate, or accept delivery | [`PIPELINE.md`](docs/human/PIPELINE.md) |
| hand an architecture decision back into the pipeline | [`ARCHITECTURE-GUIDE.md`](docs/human/ARCHITECTURE-GUIDE.md) |
| continue one named task in another coding CLI | [`WORKCTL.md`](docs/human/WORKCTL.md) |
| change a machine-facing contract or learn allowed config values | [`COMPAT.md`](docs/agent/COMPAT.md) and the adjacent JSON schema |

`SETUP.md` owns installation/runtime configuration. `PIPELINE.md` owns the project journey from
bootstrap through acceptance; do not look for a second operator runbook.

## Attribution

The `grace-*` skills are adapted from [osovv/grace-marketplace](https://github.com/osovv/grace-marketplace)
(MIT). Full notice: [`NOTICE.md`](NOTICE.md).

## Relationship to claude-config

This repo can coexist with `claude-config` (personal config, agents, global skills), but that
repository is not a setup prerequisite. Skill-path collisions still follow the fail-closed migration
described in `SETUP.md`.
