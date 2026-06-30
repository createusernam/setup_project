# Setup Guide

## Install

### One command

```bash
git clone https://github.com/createusernam/setup.git ~/.setup
bash ~/.setup/install.sh
```

That's it. `install.sh` does steps 1–3 below automatically.

---

### Manual steps (if install.sh fails)

#### 1. Clone

```bash
git clone https://github.com/createusernam/setup.git ~/.setup
```

#### 2. Register skills

Skills live in `~/.claude/skills/`. Symlink each skill directory:

```bash
for skill in ~/.setup/skills/*/; do
  ln -sf "$skill" ~/.claude/skills/"$(basename "$skill")"
done
```

Verify — in Claude Code type `/startup`. Should appear in skill list.

> **How it works**: Claude Code loads skills from `~/.claude/skills/<name>/SKILL.md`.
> There is no `skillsDirectories` setting — the only path Claude Code reads is `~/.claude/skills/`.
> Symlinks keep skills in sync with the repo (`git pull ~/.setup` → skills update automatically).

#### 3. Playwright MCP (for /build-loop)

```bash
claude mcp add playwright -- npx -y @playwright/mcp@latest --headless
```

#### 4. GH_TOKEN

```bash
cat ~/.claude/.env | grep GH_TOKEN
# If missing: echo 'GH_TOKEN=ghp_...' >> ~/.claude/.env
```

## Creating a new project

```bash
# In Claude Code:
/startup my-project-name

# Answers these questions:
# 1. Product name?
# 2. Is there a frontend? (y/n)
# 3. Tech stack?
# 4. Is architecturally complex? (y/n)
```

## Per-project first session

```bash
# 1. If product_brief.md has gaps:
/researcher

# 2. Fill product_brief.md (sections 1-5)
# Open: ~/my-project/product_brief.md

# 3. Validate with judge:
/judge product-brief

# 4. Start discovery:
/grill-with-docs

# 5. Continue per ~/.setup/PIPELINE.md
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

Follow `~/.setup/PROMPT-FORMAT.md`. Minimum viable:

```xml
<role>You are [role]. [N years experience]. [domain].</role>
<task>[One clear goal]</task>
<output_format>{ "status": "...", "data": {}, "hypotheses": [], "next_action": "" }</output_format>
<critical_reminder>[Repeat key constraint]</critical_reminder>
```

## GRACE Full (when needed)

If ≥2 of 4 criteria are true (see PIPELINE.md Branch A):

```bash
# After /planning-with-files, before /contract:
/grace-init     # creates docs/knowledge-graph.xml
/grace-plan     # creates docs/development-plan.xml
/grace-verification  # creates docs/verification-plan.xml
```

Then continue with `/contract` referencing the plan.

## Troubleshooting

**Agent ignores MODULE_CONTRACT headers**
→ Inject the contract directly into the prompt, not just as a file reference.
→ See PROMPT-FORMAT.md §7 "GRACE anchors in prompts"

**Judge always returns CONDITIONAL**
→ Check: is the product_brief.md fully filled? All 9 sections?
→ Run `/judge product-brief` with verbose output to see which criteria fail

**/design-first API doesn't match wireframe**
→ Ensure data_requirements table in Phase 1 output is complete
→ Run Phase 3 with explicit wireframe data_requirements as context

**Problem feels vague after /researcher**
→ Run Phase 2 again with more user quotes
→ If problem_depth = identity: need identity-level evidence, not just practical pain
