# Setup Guide

The automated installer is supported on Linux and Windows through WSL2. Native Windows and macOS
are not currently validated install targets; use WSL2 or the terminal/API artifact fallback.

## Install — Claude Code

### One command

```bash
git clone https://github.com/createusernam/setup_project.git ~/setup
bash ~/setup/install.sh
```

That's it. `install.sh` registers one canonical skill tree for Claude, Codex, and OpenCode, installs
their shared routing policy, exposes shared scripts, and installs `workctl` plus
`setup-skill-doctor` in `~/.local/bin/`.

Verify the cross-runtime controller:

```bash
workctl doctor
setup-skill-doctor
setup-pipeline --help
```

## Choose the runtime syntax

| Runtime | What the human enters to invoke a skill |
|---|---|
| Claude Code | `/startup my-project` or another `/skill-name` command |
| Codex | `$startup` with the project name in the request, or explicitly name the skill |
| OpenCode | ask for the skill by name or use its native `skill` tool, then provide the arguments |
| Terminal/API | load the complete `~/setup/skills/<skill-name>/SKILL.md`, then provide the goal and input files |

Restart an already open CLI after installation. If a named skill is absent, run
`setup-skill-doctor`; do not substitute a similarly named process.

---

### Manual steps (if install.sh fails)

#### 1. Clone

```bash
git clone https://github.com/createusernam/setup_project.git ~/setup
```

#### 2. Register skills

Claude discovers `~/.claude/skills/`; Codex discovers the Agent Skills standard root
`~/.agents/skills/`; OpenCode scans both. Link each root to the same source:

```bash
mkdir -p ~/.claude/skills ~/.agents/skills
for skill in ~/setup/skills/*/; do
  ln -s "$skill" ~/.claude/skills/"$(basename "$skill")"
  ln -s "$skill" ~/.agents/skills/"$(basename "$skill")"
done
python3 ~/setup/scripts/install-skill-routing.py --install \
  --source ~/setup/docs/agent/SKILL-ROUTING.md --home "$HOME"
```

Verify — in Claude Code type `/startup`. Should appear in skill list.

> Symlinks keep both discovery views in sync with the repo (`git pull ~/setup` updates every CLI).
> Do not overwrite an existing path manually. Use
> `install.sh --migrate-skill-collisions`; it backs up stale copies before linking.

#### 3. Install workctl

Skip this when `install.sh` succeeded.

```bash
mkdir -p ~/.local/bin
test ! -e ~/.local/bin/workctl
ln -s ~/setup/scripts/workctl.py ~/.local/bin/workctl
workctl doctor
```

If `~/.local/bin/workctl` already exists, inspect it rather than overwriting it. The main installer
halts on this collision.

#### 4. Playwright MCP (for /build-loop)

```bash
claude mcp add playwright -- npx -y @playwright/mcp@latest --headless
```

#### 5. GH_TOKEN

```bash
cat ~/.claude/.env | grep GH_TOKEN
# If missing: echo 'GH_TOKEN=ghp_...' >> ~/.claude/.env
```

---

## Install — OpenCode

```bash
git clone https://github.com/createusernam/setup_project.git ~/setup
bash ~/setup/install.sh
```

`install.sh` links skills into both roots OpenCode scans; both resolve to the same source. Nothing
else is needed for skill discovery.

Add to `~/.config/opencode/opencode.json` (merge with existing). Replace the example absolute path
with the output of `cd ~/setup && pwd`; do not rely on `~` expansion inside JSON. `instructions` is an
**array of file paths** OpenCode loads — not a prose string — and the paths include the
`docs/` subdirs (`install.sh` prints the exact block with absolute paths):
```json
{
  "instructions": [
    "/home/you/setup/docs/human/PIPELINE.md",
    "/home/you/setup/docs/agent/COMPAT.md"
  ],
  "model": "provider/model-id",
  "small_model": "provider/fast-model-id",
  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "@playwright/mcp@latest", "--headless"],
      "enabled": true
    }
  }
}
```

Verify: run `opencode`, type "start a new project" — startup skill should load.

> **Skills location**: skills live once in `~/setup/skills/`; the runtime roots are only symlinked
> discovery views. No per-project copies are needed.
>
> OpenCode also has a native `skill` tool — call it to load any skill's full instructions into context.

## Codex and cross-runtime continuation

Codex discovers the same setup skills through `~/.agents/skills/`. `workctl` additionally launches
the target runtime with an explicit task ID and absolute paths to portable task state. Confirm both
discovery and continuation from any repository:

```bash
workctl doctor
setup-skill-doctor
```

If a provider limit ends the current session, switch explicitly:

```bash
workctl handoff auth-refresh --to codex --next-action "Continue from the failing integration test"
workctl continue auth-refresh --runtime codex
```

The explicit task ID is required whenever a repository may contain multiple tasks.

## Creating a new project

### Claude Code

```bash
/startup my-project-name

# Confirms only bootstrap decisions:
# 1. Product display name? (defaults to project name)
# 2. Create a GitHub remote now? (default: no)
# 3. If yes: owner and visibility?
```

### OpenCode

```
"create a new project called my-project-name"
```

Startup asks the same minimal bootstrap questions, creates the project, and:
- Copies all templates from `~/setup/templates/project/`
- Generates `CLAUDE.md` with answers
- Creates `AGENTS.md → CLAUDE.md` symlink (auto, no manual step needed)
- runs `git init`; `gh repo create` runs only after explicit approval

### After creation

```bash
cd ~/my-project-name
# AGENTS.md symlink already created by startup — OpenCode reads project config immediately

# Recommended when work may span several CLIs. Run from an ordinary terminal:
workctl init <task-id> --goal "Carry <task> through the pipeline"
workctl start <task-id> --runtime claude  # launches the selected CLI
```

Do not choose a stack, frontend/backend shape, architecture complexity, risk tier, or GRACE mode in
setup. Complete discovery first. When the brief and evidence make the work shape visible, classify
the route, then enable only the model bindings required by that route:

```bash
setup-pipeline set-tier <T0..T4> --reason "<evidence-based route rationale>"
setup-pipeline set-phase <next-phase>
bash ~/.claude/scripts/model-check.sh <next-phase> .
setup-pipeline status
```

Only project-local files are edited here. `model-routing.json` and `pipeline-machine.json` are
setup-maintainer contracts: select from their declared values rather than changing them to bypass a
gate. `COMPAT.md` gives the allowed `runtime`, `model_id`, and `enabled` values.

## Setup ends; pipeline begins

At this point the installation, runtime syntax, and project bootstrap are ready. Model configuration
is intentionally deferred until the route is known.
Do not run the first phase from this guide: the shared operator loop, required artifacts, GRACE
mode, attestation and resume procedure are owned by [`PIPELINE.md`](PIPELINE.md).

For agent-authored prompts, use the portable contract in
[`../agent/PROMPT-FORMAT.md`](../agent/PROMPT-FORMAT.md). Source-file GRACE Lite and GRACE Full
planning are pipeline verification concerns, not additional install steps.

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

**Agent ignores MODULE_CONTRACT headers**
→ Inject the contract directly into the prompt, not just as a file reference.
→ See ../agent/PROMPT-FORMAT.md §7 "GRACE anchors in prompts"

**Judge always returns CONDITIONAL**
→ Check: is the product_brief.md fully filled? All 9 sections?
→ Run `/judge product-brief` with verbose output to see which criteria fail

**/design-first API doesn't match wireframe**
→ Ensure data_requirements table in Phase 1 output is complete
→ Run Phase 3 with explicit wireframe data_requirements as context

**Problem or outcome still feels vague after /researcher**
→ Return to `product_brief.md` §2 and label facts, assumptions, and open questions explicitly
→ Collect evidence appropriate to the decision and keep unresolved claims out of delivery scope
