# Setup Guide

This is the single source of truth for installing and configuring the harness. README files link
here but do not repeat the commands. Project creation and delivery begin in
[`PIPELINE.md`](PIPELINE.md).

Supported automated install targets are Linux and Windows through WSL2. Native Windows and macOS
are not currently validated; use WSL2 or the terminal/API fallback.

## Install once

The same installation serves Claude Code, Codex, and OpenCode:

```bash
git clone https://github.com/createusernam/setup_project.git ~/setup
bash ~/setup/install.sh
```

The installer registers one canonical skill tree in both discovery roots, installs the shared
routing contract, retains the legacy script links, and exposes these runtime-neutral commands in
`~/.local/bin`:

| Command | Purpose |
|---|---|
| `setup-skill-doctor` | verify skill discovery and routing across CLIs |
| `setup-pipeline` | operate the project phase/evidence ledger |
| `setup-preflight` | check phase inputs, semantics, model bindings, and human gates |
| `setup-model-check` | diagnose the binding selected for one phase |
| `setup-grace-lint` | check source-level GRACE contracts |
| `workctl` | continue one named task across CLIs |

The commands are agent-facing deterministic mechanisms and troubleshooting surfaces. After install,
the normal human interface is conversation: open an agent in a project and ask where the project is
and what to do next; the installed `pipeline-status` skill performs the checks.

If `~/.local/bin` is not on `PATH`, add it using your shell's normal configuration before
continuing. Verify the installation:

```bash
setup-skill-doctor
setup-pipeline --help
setup-pipeline values
workctl doctor
```

`setup-skill-doctor` must pass. `workctl doctor` may report a CLI as unavailable when you chose not
to install it; that does not invalidate the CLIs you do use. Restart any CLI that was open during
installation.

## Invoke a skill from any CLI

Canonical docs name the skill without a slash. Translate the name only at invocation time:

| Entry surface | Invocation |
|---|---|
| Claude Code | `/startup my-project` or `/skill-name` |
| Codex | `$startup` with the goal, or name `startup` explicitly |
| OpenCode | name the skill or load it with the native `skill` tool |
| Terminal/API | load the complete `~/setup/skills/<skill-name>/SKILL.md`, then supply the goal and referenced artifacts |

If the named skill is absent, stop and run `setup-skill-doctor`; do not silently substitute a
similar workflow. The allowed skill names are the directories printed by that command and the
installed runtime's skill list.

## Runtime-specific post-install

### Claude Code and Codex

No additional skill-discovery configuration is required. Both use the canonical links installed
above.

### OpenCode

OpenCode scans the same skill roots. Add the shared operator and compatibility instructions to
`~/.config/opencode/opencode.json`, using the absolute path returned by `cd ~/setup && pwd`:

```json
{
  "instructions": [
    "/home/you/setup/docs/human/PIPELINE.md",
    "/home/you/setup/docs/agent/COMPAT.md"
  ]
}
```

Merge this object with existing configuration; `instructions` must be an array. Global `model` and
`small_model` values are optional runtime defaults, not pipeline values. If you set them, obtain
valid exact identifiers with `opencode models [provider]`; project phase bindings remain in
`model-bindings.json`.

Verify by starting OpenCode and asking it to use the `startup` skill.

## Find an exact model ID

Do not copy the placeholder IDs from templates. Use the discovery surface belonging to the runtime
that will actually execute the phase:

| Runtime value | Where to find an accepted `model_id` |
|---|---|
| `claude` | open Claude Code and use `/model`; use the displayed full name or accepted alias |
| `codex` | open Codex and use `/model`; the picker lists models available to the current account |
| `opencode` | run `opencode models [provider]` (`provider` is optional) |
| `api` | use that provider's authenticated model-list endpoint or current official model catalog |
| `self-hosted` | use the serving runtime's model-list command/endpoint, for example its OpenAI-compatible `/v1/models` |
| `manual` | use the identifier reported by the underlying surface the human will operate |
| `custom:<lowercase-slug>` | use the adapter's documented discovery command; record that command in project docs |

The value must be non-empty and contain no whitespace. Availability is account- and runtime-specific,
so setup intentionally does not freeze a vendor model list.

## Optional browser evaluator for `build-loop`

Playwright MCP is required only for the autonomous `build-loop` route. Human-paced `tdd` does not
require it. Configure and verify it in the runtime that will host the evaluator:

| Runtime | Configure | Verify |
|---|---|---|
| Claude Code | `claude mcp add playwright -- npx -y @playwright/mcp@latest --headless` | `claude mcp list` |
| Codex | `codex mcp add playwright -- npx -y @playwright/mcp@latest --headless` | `codex mcp list` or `/mcp` in the TUI |
| OpenCode | add the JSON block below | `opencode mcp list` |
| Terminal/API | provide an equivalent Playwright/browser tool adapter | run its tool-list/health check; otherwise select `tdd` |

OpenCode configuration block:

```json
{
  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "-y", "@playwright/mcp@latest", "--headless"],
      "enabled": true
    }
  }
}
```

The Codex command and `~/.codex/config.toml` ownership follow the current official Codex MCP manual.
Do not install Playwright merely because it appears here; the operator path in `PIPELINE.md` tells
you when the selected build route needs it.

## Manual fallback when `install.sh` fails

Use this only after reading the install error. Collision failures should normally be resolved by the
installer's recoverable migration:

```bash
bash ~/setup/install.sh --migrate-skill-collisions
```

That flag's only allowed meaning is to move conflicting skill/command paths into
`~/.setup-skill-backups/<timestamp>/`; it never deletes them.

If automatic installation itself is unavailable, register the shared roots and routing contract:

```bash
mkdir -p ~/.claude/skills ~/.agents/skills ~/.local/bin
for skill in ~/setup/skills/*/; do
  ln -s "$skill" ~/.claude/skills/"$(basename "$skill")"
  ln -s "$skill" ~/.agents/skills/"$(basename "$skill")"
done
python3 ~/setup/scripts/install-skill-routing.py --install \
  --source ~/setup/docs/agent/SKILL-ROUTING.md --home "$HOME"
```

Then, only when those six destinations do not already exist, link the runtime-neutral commands:

```bash
ln -s ~/setup/scripts/check-skill-discovery.py ~/.local/bin/setup-skill-doctor
ln -s ~/setup/scripts/pipeline-state.py ~/.local/bin/setup-pipeline
ln -s ~/setup/scripts/pipeline-preflight.sh ~/.local/bin/setup-preflight
ln -s ~/setup/scripts/model-check.sh ~/.local/bin/setup-model-check
ln -s ~/setup/scripts/grace-lint.sh ~/.local/bin/setup-grace-lint
ln -s ~/setup/scripts/workctl.py ~/.local/bin/workctl
```

Otherwise rerun `install.sh` after resolving the original error. Do not overwrite an unrelated
existing command without inspecting or backing it up.

## Setup ends; the project path begins

Once `setup-skill-doctor` passes and the chosen CLI can load `startup` and `pipeline-status`, stop
using this guide. In the project directory ask the agent “What stage are we at, and what should we do next?”
For a new project, ask it to use `startup`; for an existing repository, ask it to adopt the repository
into the setup pipeline. [`PIPELINE.md`](PIPELINE.md) remains the reference for allowed values,
route decisions, gates, diagnostics, and final acceptance, but it is not required daily reading.

Runtime/model field values and provider-neutral capability profiles are owned by
[`../agent/COMPAT.md`](../agent/COMPAT.md) and the project schemas it names.

## Maintaining and publishing setup

<!-- setup:public-projection-rule -->
The private setup checkout is the editing source; the public repository is a generated, filtered
mirror. For every wider setup behavior change, update the public-safe explanation in both the
relevant `docs/human/` page and `docs/agent/` page before publishing. If the change affects the
engineering conveyor, update the handbook's `setup-pipeline.html` from `PIPELINE.md` and rebuild its
manifest. Keep private-only content in its excluded owner paths.

Commit the private source first, then run `publish-public.sh`. Never patch the generated public copy
to hide source drift; the publisher rewrites public URLs and fails closed on private markers.

## Troubleshooting

**A skill is missing or duplicated**

```bash
setup-skill-doctor
```

Fix the reported discovery root or rerun the collision migration. Do not copy a skill into another
root manually.

**A runtime cannot execute a phase**

First ask the agent where the project is and what comes next; `pipeline-status` runs the ledger and
preflight diagnostics for you. If diagnosing manually, run `setup-pipeline status`, then
`setup-preflight <phase> .`. The diagnostic names the missing artifact, allowed route, profile
binding, or human gate. Use `setup-pipeline values` to find valid phases, tiers, gates, statuses,
profiles, runtimes, and schema owners.

**OpenCode ignores shared instructions**

Confirm that `instructions` is an array of absolute file paths and restart OpenCode.

**`build-loop` cannot see Playwright**

Run the verify command from the browser-evaluator table for the evaluator's actual runtime. If the
server is unavailable, configure it there or choose `tdd`; configuring another CLI does not make the
tool available in the current one.
