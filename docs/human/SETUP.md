# Setup Guide

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
```

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

Add to `~/.config/opencode/opencode.json` (merge with existing). `instructions` is an
**array of file paths** OpenCode loads — not a prose string — and the paths include the
`docs/` subdirs (`install.sh` prints the exact block with absolute paths):
```json
{
  "instructions": [
    "~/setup/docs/human/PIPELINE.md",
    "~/setup/docs/agent/COMPAT.md"
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

# Answers these questions:
# 1. Product name?
# 2. Is there a frontend? (y/n)
# 3. Tech stack?
# 4. Is architecturally complex? (y/n)
```

### OpenCode

```
"create a new project called my-project-name"
```

Startup skill asks the same 4 questions, creates project, and:
- Copies all templates from `~/setup/templates/project/`
- Generates `CLAUDE.md` with answers
- Creates `AGENTS.md → CLAUDE.md` symlink (auto, no manual step needed)
- `git init` + `gh repo create`

### After creation

```bash
cd ~/my-project-name
# AGENTS.md symlink already created by startup — OpenCode reads project config immediately

# Recommended when work may span several CLIs. Run from an ordinary terminal:
workctl init <task-id> --goal "Carry <task> through the pipeline"
workctl start <task-id> --runtime claude  # launches the selected CLI
```

## Per-project first session

```bash
# 1. Fill all 9 neutral sections of product_brief.md using your preferred discovery process
#    or directly with stakeholders; maintain evidence-handoff.json.

# 2. If the resulting brief still has factual gaps, run /researcher and update it.

# 3. Validate the completed brief:
/judge product-brief

# 4. Start discovery:
/grill-with-docs

# 5. Continue per ~/setup/docs/human/PIPELINE.md
```

## Mandatory GRACE Lite checklist

Every file you create or modify must have:

```
// FILE: path/to/file.ext  
// START_MODULE_CONTRACT
//   PURPOSE: [one sentence what this module does]
//   SCOPE: [what operations are included]
//   DEPENDS: [M-xxx IDs or "none"]
// END_MODULE_CONTRACT
```

For Python: use `# ` prefix. For SQL: use `-- `. Adapt to language.

**Non-negotiable.** Without this, agent context degrades rapidly on multi-file tasks.

## Prompt format (for agents you write)

Follow `~/setup/docs/agent/PROMPT-FORMAT.md`. Minimum viable:

```xml
<role>You are [role]. [N years experience]. [domain].</role>
<task>[One clear goal]</task>
<output_format>{ "status": "...", "data": {}, "hypotheses": [], "next_action": "" }</output_format>
<critical_reminder>[Repeat key constraint]</critical_reminder>
```

## GRACE Full (default)

The project ledger enables GRACE Full by default. Disable it only for a bugfix or one small edit,
and record the reason in `.pipeline-state.json`. For the normal path:

```bash
# After /planning-with-files, before /contract:
/grace-init     # creates docs/knowledge-graph.xml
/grace-plan     # creates docs/development-plan.xml, docs/verification-plan.xml
```

Then deepen coverage with `/tdd` + `/judge` before large execution waves.

Then continue with `/contract` referencing the plan.

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
