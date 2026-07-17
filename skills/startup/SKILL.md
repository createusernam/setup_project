---
name: startup
description: Create new project from setup template — copies templates, pre-fills config, git init, GitHub repo creation. Invoke when user says "create project", "new project", "init project", "startup", or wants to bootstrap a new workspace.
---

# /startup — Create New Project

Creates a new project folder from the setup template and records only bootstrap decisions that are
knowable before discovery. Product shape, stack, risk tier, and GRACE Full applicability are derived
later from approved artifacts.

## Usage

```
/startup <project-name>
```

Or without args — the skill will ask for project name.

`project-name` must be a 1–64 character lowercase slug using `a-z`, `0-9`, and `-`, beginning and
ending with an alphanumeric character. Ask for a corrected name before touching the filesystem when
it does not match.

## What it does

1. Creates `~/<project-name>/` directory structure
2. Copies templates from `~/setup/templates/project/`
3. Confirms the product display name and optional GitHub remote
4. Generates pre-filled `CLAUDE.md` for the project
5. Initializes git repo
6. Creates a GitHub repo only after explicit approval
7. Initial commit

## Bootstrap questions

```
1. Product display name? (default: project name)
2. Create a GitHub remote now? (default: no)
3. If yes: which owner and visibility (`private|public`)?
```

The display name and accountable owner are non-empty free text. Discover valid GitHub owners from
the authenticated account with `gh api user --jq .login` and
`gh api user/orgs --jq '.[].login'`; do not guess an organization slug.

## Instructions

Read this prompt before executing. Then execute step by step.

### Step 1 — gather inputs

Use the project name as the display name unless the user distinguishes them. Ask the remote question
only if the user has not already requested local-only or GitHub creation. Ask owner and visibility
only when remote creation was approved.

Do not ask for frontend/backend shape, tech stack, module count, architectural complexity, risk tier,
GRACE mode, test stack, or observability here. Record those as deferred until discovery and planning.

### Step 2 — create directory structure

```bash
PROJECT_NAME="<project-name>"
PROJECT_PATH="$HOME/$PROJECT_NAME"

mkdir -p "$PROJECT_PATH"/{docs/{agents,adr},src}
```

### Step 3 — copy templates

Copy all files from `~/setup/templates/project/` to `$PROJECT_PATH/`:

```bash
cp -r ~/setup/templates/project/. "$PROJECT_PATH/"
```

### Step 4 — fill CLAUDE.md

Generate `$PROJECT_PATH/CLAUDE.md` with the bootstrap values substituted and decision fields deferred:

```markdown
# <project-name>

## Stack
Deferred until architecture planning. Do not infer a stack from the project name or idea.

## Config
- is_frontend: null # null until discovery; then true|false
- is_architecturally_complex: null # null until route selection; then true|false
- grace_mode: pending # pending|lite|full; derive from selected route

## Pipeline
See ~/setup/docs/human/PIPELINE.md

## GRACE
GRACE Lite is mandatory in source files; GRACE Full remains pending until route classification. See ~/setup/docs/agent/PROMPT-FORMAT.md for structured prompts.

## Commands
- dev: pending
- build: pending
- test: pending
```

### Step 5 — initialize product_brief.md metadata

Pre-fill the YAML metadata block in `product_brief.md`:
```yaml
product_name: "<product-name>"
created: "<today ISO>"
is_frontend: null
is_backend: null
status: draft
```

### Step 6 — git init and AGENTS.md symlink

Startup leaves model bindings disabled. After discovery determines the risk tier and route, enable
only the capability profiles required by that route. Allowed values are defined by the copied
`model-bindings.schema.json` and `~/setup/docs/agent/COMPAT.md`.

```bash
cd "$PROJECT_PATH"
ln -sf CLAUDE.md AGENTS.md      # OpenCode reads AGENTS.md
git init
git branch -m main
git add .
git commit -m "feat: init project from setup template"
```

### Step 7 — create GitHub repo (optional)

Only if the user explicitly approved remote creation, verify `gh auth status`, then run:
```bash
gh repo create "<github-owner>/$PROJECT_NAME" --<private|public> --source=. --push
```

If approval, owner, visibility, or authentication is missing, keep the project local and report the
missing decision. Never treat `GH_TOKEN` as consent.

### Step 8 — report

Print summary:
```
✓ Project created: ~/[project-name]
✓ GRACE Lite: mandatory; GRACE Full: pending route classification
✓ AGENTS.md → CLAUDE.md (OpenCode ready)
✓ product_brief.md: metadata initialized
✓ model-bindings.json + schema: created; profiles remain disabled until the route is known
✓ Product shape, stack, commands, risk tier, and GRACE mode: deferred
✓ Next step: fill the neutral 9-section brief and evidence handoff using your discovery process

Key files:
  ~/[project-name]/product_brief.md        ← portable discovery-to-delivery handoff
  ~/[project-name]/model-bindings.json     ← user-owned runtime/model selection
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
    "next_step": "follow docs/human/PIPELINE.md#human-operator-path from discovery through route classification"
  },
  "issues": []
}
```
