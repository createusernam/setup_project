# Setup v2 — Development Harness

Harness for product development with GRACE markup, МК-driven design, and LLM-as-judge verification.

**Core philosophy**: LLMs don't read docs — they follow trajectories set by structured context. This setup encodes that reality into every artifact and prompt.

---

## Install

### Claude Code

```bash
git clone https://github.com/createusernam/setup_project.git ~/.setup
bash ~/.setup/install.sh
```

`install.sh` symlinks skills into `~/.claude/skills/`, checks GH_TOKEN + Playwright MCP.
Verify: open Claude Code, type `/startup` — should appear in skill list.

### OpenCode + DeepSeek V4/Flash

```bash
git clone https://github.com/createusernam/setup_project.git ~/.setup

# Add to ~/.config/opencode/opencode.json:
# {
#   "instructions": "Process: ~/.setup/PIPELINE.md. Compat: ~/.setup/COMPAT.md.",
#   "mcp": {
#     "playwright": { "type": "local", "command": ["npx", "@playwright/mcp@latest", "--headless"] }
#   }
# }

# Per project — symlink AGENTS.md so OpenCode reads it:
ln -sf CLAUDE.md AGENTS.md
```

Skills work via mention in chat. Multi-agent = sequential turns with `research-state.json` as handoff. See `COMPAT.md` for full guide.

### Any LLM (terminal / API)

Clone repo. Paste `SKILL.md` content directly into your prompt. Human = orchestrator. See `COMPAT.md §Terminal`.

---

## What's new vs claude-config

| Feature | v1 (claude-config) | v2 (this repo) |
|---------|-------------------|----------------|
| GRACE | Optional (≥2/4 gate) | GRACE Lite mandatory always |
| Starting artifact | Free-form brief | `value_proposition.md` (МК-structured) |
| Research | Implicit in grill | Explicit `/researcher` 3-phase flow |
| Design | design-rubric one-time | `/design-first`: wireframe → approve → API contract |
| Verification | human review | `/judge` LLM-as-judge (isolated evaluator) |
| Agent outputs | free-form | Structured JSON with hypotheses (superposition) |
| Prompt format | intuitive | `PROMPT-FORMAT.md` standard with attention management |

## Quick start

### New machine

```bash
git clone https://github.com/createusernam/setup_project.git ~/.setup
```

### New project

```
/startup <project-name>
```

The skill:
1. Creates `~/<project-name>/` with full template
2. Asks 5 questions (frontend? stack? МК? etc.)
3. Pre-fills CLAUDE.md and value_proposition.md metadata
4. Git init + GitHub repo creation

### First work session

```
1. Fill value_proposition.md  (sections 1-5 minimum)
   OR run /researcher to discover МК first

2. /judge value-proposition   (validate before proceeding)

3. /grill-with-docs           (with value_proposition.md as primary input)

4. Continue per PIPELINE.md
```

## Directory structure

```
setup/
├── PIPELINE.md           # Process source of truth
├── PROMPT-FORMAT.md      # Structured prompt standard
├── README.md
│
├── COMPAT.md             # Cross-model/CLI guide + model routing
├── skills/
│   ├── startup/          # /startup — new project creation
│   ├── researcher/       # /researcher — general multi-agent research (4 phases)
│   ├── judge/            # /judge — LLM-as-judge evaluation
│   └── design-first/     # /design-first — wireframe → API contract
│
├── agents/
│   ├── researcher.md     # Research persona
│   └── evaluator.md      # Judge persona (always isolated)
│
└── templates/
    ├── project/          # Copied to new projects
    │   ├── CLAUDE.md
    │   ├── product_brief.md       # pipeline entry point (methodology-agnostic)
    │   ├── contract.json
    │   └── docs/
    │       ├── knowledge-graph.xml
    │       ├── development-plan.xml
    │       ├── verification-plan.xml
    │       └── agents/
    │           ├── domain.md
    │           ├── issue-tracker.md
    │           └── triage-labels.md
    └── prompts/
        └── structured-prompt-template.md
```

## 8 requirements — how they're met

| Requirement | Implementation |
|-------------|---------------|
| 1. GRACE in all projects | GRACE Lite mandatory (MODULE_CONTRACT in every file). GRACE Full optional (≥2/4). |
| 2. Product brief as input | `product_brief.md`. Fill using your product discovery process. Starting artifact for all projects. |
| 3. Design-first → API → contract | `/design-first`: wireframe → human approval → api-contract.json → contract |
| 4. TDD and good practices | Inherited from claude-config: `/tdd`, `/contract`, `/build-loop` |
| 5. Harness practices | Orchestrator/worker separation, State-First, XML anchors. No LangChain — Claude Code natively implements the graph (Task tool = node, skills = steps, build-loop = generator-evaluator). |
| 6. Researcher agent flow | `/researcher`: 4-phase multi-agent flow (decompose → parallel workers → consensus → synthesis). Not МК-specific — general purpose with `--mode` flag. |
| 7. Formalized output + verification | Structured JSON with `hypotheses[]` (superposition). `/judge` LLM-as-judge (isolated evaluator, different model). |
| 8. Structured prompt format | `PROMPT-FORMAT.md`: role → context → task → superposition → JSON schema → critical anchor. Works across Claude/DeepSeek/GLM. |

## Cross-model / no LangChain

Works across Claude Code, OpenCode + DeepSeek, and any terminal LLM. See `COMPAT.md`.

No LangChain/LangGraph — Claude Code natively provides what they offer (agent graph, state, parallel execution) without an extra service layer or Python dependency. For OpenCode: sequential turns + `research-state.json` as State handoff.

**Model routing** (Архитектура=Opus, Фронт=GLM 5.2, Бэк=DeepSeek V4, Ресёрч-воркеры=DeepSeek Flash):

| Task | Model |
|------|-------|
| Orchestrator, contract, judge | Claude Opus 4.6+ |
| Backend code | DeepSeek V4 |
| Frontend code | GLM 5.2 / DeepSeek V4 |
| Research workers | DeepSeek Flash |
| Research synthesis | Claude Sonnet |

## Relationship to claude-config

This repo extends, does not replace `claude-config`. 

- `claude-config` = personal config, agents, global skills
- `setup` = project template + new process skills

Install both:
```bash
git clone https://github.com/createusernam/claude-config.git ~/.claude
git clone https://github.com/createusernam/setup_project.git ~/.setup
```
