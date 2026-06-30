# Cross-Model / Cross-CLI Compatibility

This setup runs on three runtimes. Skills and artifacts are the same — execution differs.

## Runtime Matrix

| Feature | Claude Code | OpenCode + DeepSeek | Terminal (manual) |
|---------|------------|---------------------|-------------------|
| Skill invocation | `/skill-name` | Mention skill name in chat | Paste SKILL.md body |
| Agent spawning | `Task` tool | Sequential turns with role switch | Human orchestrates |
| State handoff | `Task` result | `research-state.json` read at turn start | Human copies JSON |
| PLAN-CONFIRM | inline in skill | Explicit "Confirm plan?" message | Human reads plan |
| Parallel agents | Parallel `Task` calls | Sequential (simulate with batch) | Sequential turns |
| GRACE markup | Agent writes directly | Agent outputs, human reviews diff | Human applies |
| Artifacts | Auto-saved by skill | Agent outputs JSON, human saves | Human saves |

---

## Agent Team Composition

**Collegium principle**: same model for coder + reviewer = blind-spot agreement. They converge on shared errors. Different model networks see different failure modes.

> "Coder and reviewer from the same network agree to ignore errors — need a collegium of different networks."
> "Without a judge, the collegium picks poorly."

**Required: different models per role.**

| Role | Model | Scope | Why |
|------|-------|-------|-----|
| **ORCHESTRATOR / ACCEPTOR** | Claude Opus 4.6+ | PBS, contract, final acceptance | Best reasoning for goal decomposition |
| **RESEARCHER (synthesis)** | Claude Sonnet | Multi-source synthesis | Cost-effective reasoning |
| **RESEARCH WORKERS** | DeepSeek Flash | Parallel desk research | Fast, cheap, parallel |
| **BACKEND IMPLEMENTER** | DeepSeek V4 | Code ≤200 lines per call | Best code/cost ratio |
| **FRONTEND IMPLEMENTER** | GLM 5.2 | React/UI code | Long context > other small models |
| **TEST OWNER / REVIEWER** | GLM 5.2 | Quality check, test runs | Different from backend implementer |
| **JUDGE / EVALUATOR** | Claude Opus (isolated) | Final verification | Isolated context, no generator bias |

**Note for OpenCode**: if GLM and DeepSeek are both available, use DeepSeek V4 for backend implementer and GLM for test-owner. If only one model is available per role, switch the model between turns (different system prompt = different "model" in terms of trajectory).

---

## Handoff Protocol

Every agent call ends with `handoff.json`:

```json
{
  "agent_role": "backend-implementer",
  "model_used": "deepseek-v4",
  "done": ["implemented auth middleware", "added MODULE_CONTRACT"],
  "files_touched": ["src/auth/middleware.ts", "src/auth/middleware.test.ts"],
  "uncertain_about": ["edge case: concurrent login from same user — need test-owner to verify"],
  "test_status": "pass",
  "collegium_verdict": "needs-review",
  "next_agent": "test-owner",
  "block_sizes": { "max_file_lines": 187 }
}
```

Test-owner reads handoff.json and either:
- `AGREE` — confirms implementation, adds tests
- `DISAGREE: [reason]` — flags issues, loops back to implementer

---

## Model Routing Table

| Task | Primary | Fallback |
|------|---------|----------|
| Orchestrator, architecture, PBS | Claude Opus 4.6+ | Claude Sonnet |
| Backend code (≤200 lines) | DeepSeek V4 | Claude Sonnet |
| Frontend code (React/UI) | GLM 5.2 | DeepSeek V4 |
| Research workers (parallel) | DeepSeek Flash | DeepSeek V4 |
| Research synthesis | Claude Sonnet | DeepSeek V4 |
| Test-owner / reviewer | GLM 5.2 | Claude Sonnet |
| Judge / evaluator | Claude Opus (isolated) | Claude Sonnet (isolated) |
| Triage / classification | DeepSeek Flash | Any |

---

## Claude Code (primary)

Skills work natively. Install: `bash ~/.setup/install.sh`

```bash
/startup      /researcher     /judge     /design-first
```

Agents spawn via `Task` / `Agent` tool. Parallel research = parallel Task calls in one message.

Collegium in Claude Code:
```
Task("backend-implementer", model="deepseek-v4", ...)  →  handoff.json
Task("test-owner", model="glm-5.2", reads=handoff.json)  →  test verdict
Task("judge", model="opus", isolated=true)  →  final verdict
```

---

## OpenCode + DeepSeek

### Install

```bash
git clone https://github.com/createusernam/setup.git ~/.setup

# Per project:
ln -sf CLAUDE.md AGENTS.md

# Register in ~/.config/opencode/opencode.json:
# {
#   "$schema": "https://opencode.ai/config.json",
#   "instructions": "Process: ~/.setup/PIPELINE.md. Compat: ~/.setup/COMPAT.md.",
#   "mcp": {
#     "playwright": { "type": "local", "command": ["npx", "@playwright/mcp@latest", "--headless"], "enabled": true }
#   }
# }
```

### Skill invocation

No `/skill-name` syntax. Instead:

```
Option A — in chat:
  "Run /researcher for [topic]. See ~/.setup/skills/researcher/SKILL.md."

Option B — AGENTS.md includes skill reference:
  "## Available skills
  researcher: ~/.setup/skills/researcher/SKILL.md"
```

### Sequential Collegium

OpenCode has no parallel Task tool. Simulate collegium with sequential turns, switching active model:

```
Turn 1 — [ORCHESTRATOR: Opus/Sonnet]
  Goal: decompose task into PBS leaves. Output task_plan.md.
  PLAN_CONFIRM: present plan, wait for APPROVE.

Turn 2 — [BACKEND IMPLEMENTER: DeepSeek V4]
  Goal: implement PBS_LEAF_1a. Read task + contract.json.
  Output: code + handoff.json.

Turn 3 — [TEST-OWNER: GLM 5.2]  ← switch model here
  Goal: verify PBS_LEAF_1a meets contract. Read handoff.json + code.
  Output: AGREE/DISAGREE + test results.

Turn 4 — [JUDGE: Opus, fresh context]  ← new conversation
  Goal: validate feature against contract.json.
  Output: judge-report.json.
```

Each turn: new role activation (first sentence). State passed via file.

### PLAN-CONFIRM in OpenCode

Before each phase, output:

```json
{
  "status": "needs_approval",
  "goal_understood": "...",
  "plan": [
    { "step": 1, "action": "...", "rationale": "..." }
  ],
  "PLAN_CONFIRM": "Type APPROVE to proceed or describe changes"
}
```

---

## Pure Terminal (no Claude Code / OpenCode)

Human = orchestrator. Each agent role = separate LLM call.

1. Open SKILL.md from `~/.setup/skills/<skill>/SKILL.md`
2. Send each phase as separate prompt with role activation (first sentence = role)
3. Copy JSON output between turns manually
4. Save state to `research-state.json` yourself

Works with any LLM that handles JSON output.

---

## State-First Design

All skills use state files as Belief State anchors.

```json
// research-state.json
{
  "version": 1,
  "question": "...",
  "phase": "decompose | research | consensus | synthesis | validation | done",
  "distortions_found": [],
  "clarified_question": "...",
  "assumptions_to_validate": [],
  "workers": [],
  "worker_findings": {},
  "contradictions": [],
  "synthesis": null,
  "judge_report": null,
  "open_questions": [],
  "updated_at": "ISO timestamp"
}
```

**Why State-First:**
- LLM thinks in state transitions, not event streams
- State file = Belief State anchor across turns and agents
- Agent starts each turn: "Read current state → produce next state"
- Verification = read state dump, not trace code

---

## Artifacts Compatibility

All artifacts are plain files — compatible across all runtimes:

| Artifact | Format | Role |
|----------|--------|------|
| `product_brief.md` | Markdown | Starting artifact |
| `research-state.json` | JSON | Research handoff |
| `CONTEXT.md` | Markdown | Discovery output |
| `task_plan.md` | Markdown | PBS task tree |
| `contract.json` | JSON (sha256-locked) | Build gate |
| `handoff.json` | JSON | Agent-to-agent handoff |
| `judge-report.json` | JSON | Evaluation result |
| `api-contract.json` | JSON | Design-first output |
| GRACE markup | Comments in code | Context anchors |
| `docs/*.xml` | XML | GRACE Full |

---

## Prompt Format Across Models

`PROMPT-FORMAT.md` applies to all models.

**DeepSeek**: XML-structured prompts. JSON output more reliable when schema is explicit in `<output_format>`.

**GLM**: add `<language>Russian for UI copy, English for code</language>` in `<belief_state>`.

**Flash models** (research workers): shorter prompts, explicit sub-question scope, no multi-hypothesis — findings + sources + confidence only.

**Any model for judge role**: always fresh context, no conversation history from the generator session.
