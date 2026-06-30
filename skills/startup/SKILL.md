---
name: startup
description: Create new project from setup template — copies templates, pre-fills config, git init, GitHub repo creation. Invoke when user says "create project", "new project", "init project", "startup", or wants to bootstrap a new workspace.
---

# /startup — Create New Project

Creates a new project folder from the setup template, configures GRACE Lite, and asks key setup questions.

## Usage

```
/startup <project-name>
```

Or without args — the skill will ask for project name.

## What it does

1. Creates `~/<project-name>/` directory structure
2. Copies templates from `~/.setup/templates/project/`
3. Asks 5 setup questions
4. Generates pre-filled `CLAUDE.md` for the project
5. Initializes git repo
6. Creates GitHub repo (if GH_TOKEN available)
7. Initial commit

## Questions asked

```
1. Product name?
2. Is there a frontend? (y/n)
3. Tech stack? (e.g. React + Express + Postgres)
4. Is architecturally complex? (≥5 modules with cross-deps) (y/n)
```

## Instructions

Read this prompt before executing. Then execute step by step.

### Step 1 — gather inputs

Ask the 4 questions above if not provided via args. Store answers.

### Step 2 — create directory structure

```bash
PROJECT_NAME="<project-name>"
PROJECT_PATH="$HOME/$PROJECT_NAME"

mkdir -p "$PROJECT_PATH"/{docs/{agents,adr},src}
```

### Step 3 — copy templates

Copy all files from `~/.setup/templates/project/` to `$PROJECT_PATH/`:

```bash
cp -r ~/.setup/templates/project/. "$PROJECT_PATH/"
```

### Step 4 — fill CLAUDE.md

Generate `$PROJECT_PATH/CLAUDE.md` with answers substituted:

```markdown
# <project-name>

## Stack
<tech-stack>

## Config
- is_frontend: <y/n>
- is_architecturally_complex: <y/n>

## Pipeline
See ~/.setup/PIPELINE.md

## GRACE
GRACE Lite mandatory. See PROMPT-FORMAT.md for structured prompts.

## Commands
- dev: <fill-in>
- build: <fill-in>
- test: <fill-in>
```

### Step 5 — fill product_brief.md metadata

Pre-fill the YAML metadata block in `product_brief.md`:
```yaml
product_name: "<product-name>"
created: "<today ISO>"
is_frontend: false
is_backend: false
status: draft
```

### Step 6 — git init and AGENTS.md symlink

```bash
cd "$PROJECT_PATH"
ln -sf CLAUDE.md AGENTS.md      # OpenCode reads AGENTS.md
git init
git branch -m main
git add .
git commit -m "feat: init project from setup template"
```

### Step 7 — create GitHub repo (optional)

If GH_TOKEN is set:
```bash
gh repo create "<github-account>/$PROJECT_NAME" --private --source=. --push
```

### Step 8 — report

Print summary:
```
✓ Project created: ~/[project-name]
✓ GRACE Lite: active (MODULE_CONTRACT required in all files)
✓ AGENTS.md → CLAUDE.md (OpenCode ready)
✓ product_brief.md: ready to fill
✓ Next step: fill product_brief.md → /methodology or /grill-with-docs

Key files:
  ~/[project-name]/product_brief.md        ← fill first
  ~/[project-name]/CLAUDE.md              ← project config
  ~/[project-name]/AGENTS.md              ← → CLAUDE.md symlink
  ~/[project-name]/docs/agents/domain.md  ← domain terminology
```

## Output

```json
{
  "status": "success",
  "data": {
    "project_path": "~/...",
    "github_url": "https://github.com/...",
    "next_step": "fill product_brief.md → methodology or grill-with-docs"
  },
  "issues": []
}
```
