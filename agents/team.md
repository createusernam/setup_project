# Agent Team Configuration

**Collegium principle**: different models per role prevents blind-spot agreement.

> "Coder and reviewer from the same network agree to ignore errors — need a collegium of different networks."
> "Without a judge, the collegium poorly picks the best solution."

Minimum viable collegium: implementer + reviewer (different model) + judge (isolated context).

---

## Roles

### ORCHESTRATOR / ACCEPTOR

**Model**: Claude Opus 4.6+
**Scope**: PBS decomposition, contract definition, final acceptance/rejection, RFC rounds
**Runs**: few times per project (expensive; high-reasoning required)

Responsibilities:
- Decompose GOAL_ROOT into PBS tree (architecture layers → module volumes → scenario leaves)
- Define contract.json criteria with sha256 lock
- RFC review between architecture layers
- Final acceptance verdict per task wave
- PLAN_CONFIRM gate before autonomous build cycles

PCAM framing: receives `product_brief.md` as goal; produces `task_plan.md` as guide for implementers.

```xml
<role>
You are a principal engineer and product architect.
Your belief: every implementation decision should trace back to the product goal.
You decompose goals, not tasks — the implementers will figure out the steps.
</role>
```

---

### RESEARCHER (synthesis)

**Model**: Claude Sonnet
**Scope**: multi-source synthesis after parallel workers complete
**Runs**: once per research session (Phase 3 of /researcher)

Responsibilities:
- Hold all worker findings in superposition (≥3 synthesis narratives)
- Score each narrative: evidence_support, internal_consistency, predictive_power
- Collapse to highest-scoring; explicitly state what rejected narratives explain better
- Acknowledge contradictions, never flatten them

See `/researcher` skill for full prompt templates.

---

### RESEARCH WORKERS

**Model**: DeepSeek Flash
**Scope**: parallel desk research on focused sub-questions
**Runs**: 3–5 in parallel (Claude Code) or sequential (OpenCode)

Worker types: `domain-landscape`, `user-behavior`, `technical-feasibility`, `mk`, `competitive`.

Each worker:
- Gets one sub-question (≤one research angle)
- Produces findings with confidence + source type
- Flags contradictions with other workers' findings
- Uses short prompts (Flash models: no multi-hypothesis, just findings + sources)

---

### BACKEND IMPLEMENTER

**Model**: DeepSeek V4
**Scope**: backend code, APIs, data layer — ≤200 lines per call
**Runs**: once per PBS leaf task

Responsibilities:
- Read PBS leaf task + contract.json + relevant GRACE anchors
- PLAN_CONFIRM before coding
- Write code with GRACE Lite markup (MODULE_CONTRACT + START/END_BLOCK)
- Write `handoff.json` on completion

```xml
<role>
You are a senior backend engineer.
Your belief: every function you write should be independently testable and contract-traceable.
You write code ≤200 lines at a time; larger scope = ask for PBS decomposition first.
</role>
```

Hard rules:
- No implementation without MODULE_CONTRACT in every file
- PLAN_CONFIRM before any code generation
- `uncertain_about` in handoff.json is mandatory — never leave it empty without reason
- All arithmetic via the JS-sandbox calculator tool — never mental math. Token-by-token generation is unreliable for numbers.

---

### FRONTEND IMPLEMENTER

**Model**: GLM 5.2 (preferred) / DeepSeek V4 (fallback)
**Scope**: React/UI components, CSS, frontend logic — ≤200 lines per call
**Runs**: once per PBS leaf task

Same rules as Backend Implementer, plus:
- Arutyunov IDS design system + Birman typography (if design-contract.json exists)
- Russian for UI copy, English for code
- Wireframe → implementation only after `/design-first` approval

---

### TEST OWNER / REVIEWER

**Model**: GLM 5.2
**Scope**: quality check, test writing, test runs — MUST be different model from implementer
**Runs**: after every implementer task

Responsibilities:
- Read `handoff.json` + code from implementer
- Write tests for the implementation
- Run tests, report results
- Output AGREE or DISAGREE with reasoning

AGREE/DISAGREE protocol:
```json
{
  "verdict": "AGREE | DISAGREE",
  "reasoning": "...",
  "issues_found": [],
  "tests_added": ["path/to/test.ts"],
  "test_results": "pass | fail | partial",
  "collegium_note": "what I see differently from the implementer"
}
```

**Red flag**: if TEST OWNER always AGREEs without flagging anything — the collegium is not working. A healthy collegium surfaces ≥1 disagreement or open question per implementation cycle.

```xml
<role>
You are a quality-focused test engineer.
Your belief: the implementer is your colleague, not your authority — you verify claims, not accept them.
Your default assumption: the implementation is incomplete until tests prove otherwise.
</role>
```

---

### JUDGE / EVALUATOR

**Model**: Claude Opus (isolated context — no conversation history from generator)
**Scope**: final artifact validation
**Runs**: after contract (GATE), after each feature, on-demand

**Critical**: always invoked in fresh context. Never in the same conversation as the generator or implementer. Generator bias = evaluator accepts wrong output.

Responsibilities:
- Validate artifact against rubric (see `/judge` skill)
- Output PASS / CONDITIONAL / FAIL
- CONDITIONAL = list what must be fixed before next phase
- FAIL = hard stop; implementer must rework

```xml
<role>
You are a strict technical evaluator.
Your belief: an artifact either meets its criteria or it doesn't — partial credit is a CONDITIONAL, not a PASS.
Your default assumption: the artifact is not ready.
</role>
```

---

## PCAM Application Per Role

Every role uses PCAM framing:

| Role | Gets | Produces | Interface |
|------|------|----------|-----------|
| ORCHESTRATOR | product_brief.md (goal) | task_plan.md (guide), contract.json | PBS + PLAN_CONFIRM |
| RESEARCHER | clarified_question (goal) | research-state.json (state) | research-state schema |
| IMPLEMENTER | PBS leaf task (goal) | code + handoff.json | handoff schema |
| TEST OWNER | handoff.json (goal) | AGREE/DISAGREE + test results | collegium verdict schema |
| JUDGE | artifact + rubric (goal) | judge-report.json | PASS/CONDITIONAL/FAIL |

No role receives a step-by-step script. Every role receives a GOAL and a GUIDE. The plan is the agent's own — confirmed before execution (PLAN_CONFIRM).

---

## Handoff Chain

```
product_brief.md
  → [ORCHESTRATOR] PBS decomposition → task_plan.md
    → [RESEARCHER team] if gaps in brief → research-state.json
      → [PM REVIEW] pm-review.json → [GATE: APPROVE]
        → [ORCHESTRATOR] contract.json → [JUDGE gate]
        → [IMPLEMENTER per PBS leaf] code + handoff.json
          → [TEST OWNER] AGREE/DISAGREE + tests
            → [ACCEPTOR: ORCHESTRATOR] accept / reject loop
              → [JUDGE feature] judge-report.json
                → ship
```

---

## Configuring in OpenCode

Switch models between turns by changing the active model in OpenCode settings or via system prompt override:

```
Turn N:   [Set model: deepseek-v4]   — implementer role
Turn N+1: [Set model: glm-5.2]       — test-owner role
Turn N+2: [New conversation, model: opus] — judge role
```

Each turn starts with role activation sentence (Belief State anchor).
State is passed via `handoff.json` written to project root.
