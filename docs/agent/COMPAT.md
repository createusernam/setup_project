# Cross-Model / Cross-CLI Compatibility

This setup runs on three runtimes. Skills and artifacts are the same — execution differs.

## Runtime Matrix

| Feature | Claude Code | OpenCode + DeepSeek | Terminal (manual) |
|---------|------------|---------------------|-------------------|
| Skill invocation | `/skill-name` | Mention skill name in chat | Paste SKILL.md body |
| Agent spawning | `Task` tool | `task` tool (`subagent_type: explore\|general`) | Human orchestrates |
| State handoff | `Task` result | `research-state.json` read at turn start | Human copies JSON |
| PLAN-CONFIRM | inline in skill | Explicit "Confirm plan?" message | Human reads plan |
| Parallel agents | Parallel `Task` calls | Parallel `task` tool calls (`subagent_type: explore\|general`), fresh context each | Sequential turns |
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

Skills work natively. Install: `bash ~/setup/install.sh`

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
git clone https://github.com/createusernam/setup_project.git ~/setup
bash ~/setup/install.sh        # symlinks skills to ~/.claude/skills/
```

OpenCode discovers skills from `~/.claude/skills/` — the same path Claude Code uses. `install.sh` handles both CLI.

Add to `~/.config/opencode/opencode.json`. `instructions` is an **array of file paths**
(OpenCode loads each file), not a prose string — and the paths must include the `docs/`
subdirs. `install.sh` prints the exact block with absolute paths for your machine:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": [
    "~/setup/docs/human/PIPELINE.md",
    "~/setup/docs/agent/COMPAT.md"
  ],
  "model": "deepseek/deepseek-v4-pro",
  "small_model": "deepseek/deepseek-v4-flash",
  "mcp": {
    "playwright": { "type": "local", "command": ["npx", "@playwright/mcp@latest", "--headless"], "enabled": true }
  }
}
```
If OpenCode does not expand `~` in these paths, use the absolute path `install.sh` prints.

Per-project: startup skill creates `AGENTS.md → CLAUDE.md` symlink automatically — no manual step needed.

Verify: `opencode` → "start a new project" → startup skill should load.

### Skill invocation

No `/slash` syntax. Skills are invoked by name or purpose:

```
"Run the researcher skill for e-commerce market"
"Judge this contract against the rubric"
"Use design-first to wireframe the landing page"
```

OpenCode's native `skill` tool loads any skill's full instructions into context. Use `skill({ name: "startup" })` or describe the task and the model maps it to the right skill.

Alternatively — reference the path directly:
```
"Run ~/setup/skills/researcher/SKILL.md for e-commerce market research"
```

### Parallel Collegium — for research / broad-breadth tasks

OpenCode supports parallel agents via the `task` tool: multiple `task` calls in a single message run concurrently, each with a fresh, isolated context window (independent `ses_id`). Available `subagent_type`: `explore` (fast, read-only search), `general` (multi-step, write access). Use `explore` for research workers, `general` for synthesis/judge.

```
[ORCHESTRATOR: Opus/Sonnet] — single turn
   decompose → write research-state.json
   ↓ (one message, multiple task calls)
[WORKER-1: general]  [WORKER-2: general]  [WORKER-3: general]   ← parallel, isolated
   each reads sub_question from state, writes findings to file
   ↓
[ORCHESTRATOR] reads all findings → synthesis
   ↓
[JUDGE: general, fresh context via new task call] validates
```

### Sequential Collegium — for build-loop (handoff-dependent turns)

When each agent must read the prior's output (implementer → test-owner → judge), chain `task` calls across turns. State passes via files (`handoff.json`, `contract.json`, `judge-report.json`). Switch the active model per turn via opencode.json `model`/`small_model` or per-call overrides.

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

Each turn: new role activation (first sentence). State passed via file. To get a fresh context for the judge (no generator bias), start a new `task` call rather than continuing the same conversation.

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

1. Open SKILL.md from `~/setup/skills/<skill>/SKILL.md`
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

## State format — JSON vs XML

Two findings that look contradictory, and the line between them. Get this wrong in either direction
and the agent either destroys its own state or goes blind on a long context.

| Finding | Source | About |
|---------|--------|-------|
| Models overwrite **markdown** far more readily than JSON | Anthropic Applied AI talk, May 2026 | **writing** — braces make a file feel structural, and the model treats it as data, not prose to rewrite |
| **JSON degrades as read-context**; prefer XML-like markup | OpenAI GPT-4.1 prompting guide (`#delimiters`); GRACE | **reading** — on long context the model ends up matching braces, attention drifts, comprehension collapses |

Both are true because they describe different operations. The rule that satisfies both:

- **JSON — control state.** Small (≲5k tokens), schema'd, parsed by scripts, read whole, and it must
  survive an agent's urge to "tidy" it: `contract.json`, `critique.json`, `handoff.json`,
  `.pipeline-state.json`, `judge-report.json`, `api-contract.json`.
- **XML-like — everything the agent reads in bulk to navigate.** Graphs, plans, verification surfaces,
  logs and traces: `docs/knowledge-graph.xml`, `docs/development-plan.xml`,
  `docs/verification-plan.xml`, GRACE in-code anchors, `[Module][function][BLOCK]` log lines.
- **Markdown — for humans.** `product_brief.md`, `CONTEXT.md`, `task_plan.md`, gate diagrams. Expect
  agents to rewrite it freely; never make it the sole carrier of state a later phase depends on.

**The threshold, stated once:** if an artifact will be handed to a model as context and exceeds
roughly 5k tokens, it must not be JSON. Long worker findings, captured traces, accumulated research —
write them as XML-like sections with named anchors, not as growing JSON arrays. A `research-state.json`
whose `worker_findings` has swollen to 30k tokens is the exact failure mode both findings warn about:
maximally overwrite-resistant, and unreadable by the model that has to synthesize it.

Do **not** mirror a canonical domain artifact into both formats merely to get both properties. Two
independent copies of one state are a drift bug. The explicit exception is
`/planning-with-files`: its Markdown files are the human views and the adjacent JSON files are
schema-checked control mirrors updated atomically by that skill. They are one versioned artifact
pair, not competing sources of domain truth.

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
