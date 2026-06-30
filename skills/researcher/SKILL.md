# /researcher — Multi-Agent Research Flow

General-purpose research skill. Multiple agents explore in parallel, reach consensus, synthesize.

**Not МК-specific.** МК research is one application via `--mode mk`. Works for: market research, technical feasibility, competitive analysis, user behavior, domain knowledge, any open question.

## Usage

```
/researcher [--mode mk|market|technical|user|domain|custom]
            [--question "research question"]
            [--angles "angle1, angle2, angle3"]
            [--context "relevant background"]
```

Without args: orchestrator decomposes the question automatically.

## Output

`docs/research-state.json` — shared state across all phases
`docs/research-report.md` — human-readable synthesis

## Architecture

```
[ORCHESTRATOR] Decompose → Plan → PLAN-CONFIRM
      ↓
[WORKER-1] [WORKER-2] [WORKER-3]  ← parallel (Claude Code) or sequential (OpenCode)
      ↓
[ORCHESTRATOR] Consensus check → Synthesis (superposition → collapse)
      ↓
[JUDGE] Validation (isolated context)
```

**State-First**: all phases read/write `research-state.json`. Each worker produces next state, not events.

## Execution by runtime

See `COMPAT.md` for full cross-model guide.

**Claude Code**: phases run as parallel Task calls. Model routing: Flash workers, Sonnet synthesis, Opus orchestrator.

**OpenCode**: sequential turns. Each phase = one turn. Start each with role activation.

**Terminal**: human orchestrates. Each phase = separate LLM call. Copy JSON between calls.

---

## Phase -1 — Metamodel Distortion Check

**Goal**: clean the research question before decomposing it. Distortions in the question propagate into all downstream findings.

**Model**: Claude Sonnet / Opus (linguistic analysis)

**When to run**: always, before Phase 0. Adds ≤2 minutes, saves hours of research in wrong direction.

Check for NLP distortions that hide missing requirements:

| Distortion | Pattern | Question to ask |
|------------|---------|-----------------|
| **Omission** (passive) | "the feature needs to be built" | Who builds? For whom? What exactly? |
| **Nominalization** | "user onboarding", "the implementation" | Onboard to what? Implement what, how, who? |
| **Modal operator** | "must", "can't", "should" | Who says? What happens if we don't? |
| **Presupposition** | "since users need X" | Do they? What's the evidence? |
| **Omitted performative** | "this is important", "we can't do that" | To whom? Who decided? On what basis? |
| **Cliché** | "best practices", "modern approach" | Which ones specifically? Why those? |

**Prompt template:**

```xml
<role>
You are a requirements analyst trained in NLP metamodel analysis.
Your goal: surface hidden assumptions and missing specifics in a research question,
so that downstream research doesn't investigate the wrong thing.
</role>
<belief_state>
Research question: [QUESTION]
Context: [CONTEXT if any]
</belief_state>
<goal>
GOAL_ROOT: Identify every place where the question hides an assumption, omits an agent,
or uses a nominalization that blocks precise research.
Not success: listing distortions without clarifying what information would fix them.
</goal>
<guide>
For each distortion: name the type, quote the phrase, state the missing information,
propose a clarified version. Aggregate into a distortion-free rewrite of the question.
</guide>
<think_before_answering>
Read the question 3 times with different lenses:
1. "Who is doing what to whom?" — surface omitted agents
2. "What assumptions are stated as facts?" — surface presuppositions
3. "What process has been turned into a noun?" — surface nominalizations
</think_before_answering>
<output_format>
{
  "status": "success",
  "distortions_found": [
    {
      "type": "nominalization | omission | modal_operator | presupposition | omitted_performative | cliche",
      "phrase": "...",
      "missing_info": "...",
      "clarification": "..."
    }
  ],
  "clarified_question": "distortion-free version of the original question",
  "assumptions_to_validate": ["assumption 1", "assumption 2"],
  "original_question": "..."
}
</output_format>
<critical_reminder>
If the question is already clear and specific, output distortions_found: [] and
clarified_question = original_question. Don't invent distortions.
</critical_reminder>
```

**After Phase -1**: update `research-state.json` with `distortions_found`, `clarified_question`, `assumptions_to_validate`. Proceed to Phase 0 using `clarified_question`, not the original.

---

## Phase 0 — Orchestrator: Decompose

**Goal**: break research question into N focused sub-questions, one per worker.

**Model**: Claude Opus / Sonnet (orchestrator tier)

**Prompt template:**

```xml
<role>
You are a research director with 10+ years designing multi-agent research programs.
Your job: decompose a research question into N focused, non-overlapping sub-questions,
each answerable by a specialized worker agent in one focused session.
</role>
<context>
Research question: [QUESTION]
Background: [CONTEXT]
Mode: [MODE]
</context>
<task>
1. Identify 3–5 distinct research angles for this question
2. For each angle: define scope, worker type, expected output format
3. Identify what each worker needs from others (dependencies)
4. Produce PLAN-CONFIRM for human approval
</task>
<think_before_answering>
Generate 3 decomposition approaches. Score each on:
- coverage (0–1): does it cover the full question?
- independence (0–1): are sub-questions truly parallel?
- actionability (0–1): can each be researched in one session?
Select highest scoring.
</think_before_answering>
<output_format>
{
  "status": "needs_approval",
  "data": {
    "question": "...",
    "mode": "...",
    "workers": [
      {
        "id": "W1",
        "angle": "domain-landscape",
        "sub_question": "...",
        "scope": "...",
        "worker_type": "domain | user | technical | competitive | mk",
        "depends_on": [],
        "expected_output": "..."
      }
    ],
    "plan_summary": "3-sentence plan description"
  },
  "hypotheses": [],
  "selected_hypothesis": "",
  "next_action": "Type APPROVE to launch workers or describe changes"
}
</output_format>
<critical_reminder>
Sub-questions must be non-overlapping and each independently researchable.
Output valid JSON only.
</critical_reminder>
```

**After APPROVE**: write initial `research-state.json`, launch workers.

---

## Phase 1 — Workers: Parallel Research

Each worker receives:
- Their specific sub-question
- Current `research-state.json`
- Their worker type prompt (below)

**Model**: DeepSeek Flash (fast, cost-effective for desk research)

### Worker prompt template

```xml
<role>
You are a [WORKER_TYPE] researcher. You focus exclusively on [ANGLE].
Your findings feed into a multi-agent synthesis — be precise and cite sources.
</role>
<context>
Full research question: [QUESTION]
Your sub-question: [SUB_QUESTION]
Your scope: [SCOPE]
Current research state: [research-state.json content]
</context>
<task>
Research [SUB_QUESTION].
Find: evidence, counterevidence, key sources, patterns.
Be specific — vague findings block synthesis.
</task>
<constraints>
  <required>
    - At least 3 distinct evidence points
    - For each finding: confidence 0–1 + source type (desk|interview|observation|inference)
    - Flag contradictions with existing state findings
    - Explicit "I don't know" when data is absent (no inference without evidence)
  </required>
  <forbidden>
    - Findings without evidence
    - Extrapolating beyond sub-question scope
    - Suppressing contradictions to look consistent
  </forbidden>
</constraints>
<think_before_answering>
Generate 3 hypotheses about [SUB_QUESTION] before researching.
Research to confirm, deny, or refine each.
Report which survived and why.
</think_before_answering>
<output_format>
{
  "worker_id": "W1",
  "angle": "...",
  "sub_question": "...",
  "findings": [
    {
      "insight": "...",
      "evidence": "...",
      "source_type": "desk|interview|observation|inference",
      "confidence": 0.0,
      "contradicts": ["other_finding_id or null"]
    }
  ],
  "hypotheses_tested": [
    { "hypothesis": "...", "verdict": "confirmed|denied|refined", "reason": "..." }
  ],
  "key_quotes": [],
  "gaps": ["what I couldn't find"],
  "confidence_overall": 0.0
}
</output_format>
<critical_reminder>
Flag every contradiction with existing state. Output valid JSON only.
</critical_reminder>
```

**After each worker**: merge output into `research-state.json.worker_findings[worker_id]`.

### Worker type specializations

**domain-landscape** worker:
- Existing solutions, key players, market size
- What has been tried, what failed, why
- Standard approaches vs. non-standard

**user-behavior** worker:
- How people deal with the problem today
- Workarounds, hacks, abandoned attempts
- Language they use to describe the problem

**technical-feasibility** worker:
- What's technically possible, at what cost
- Existing tools, libraries, approaches
- Known failure modes

**mk** worker (МК-specific mode):
- Segment motivational conflict evidence
- P1P incompatibility evidence
- NTO candidate from user language
- МК level indicators (МК₁ / МК₁₋₂ / МК₂₋₃)

**competitive** worker:
- Who else is solving this
- Their approach and its gaps
- What they avoid and why

---

## Phase 2 — Orchestrator: Consensus Check

Before synthesis, identify contradictions across workers. Orchestrator role.

**Model**: Claude Sonnet

```xml
<role>
You are a research synthesis director. You do not take sides — you map disagreements.
</role>
<context>
All worker findings: [research-state.json.worker_findings]
</context>
<task>
1. Find all contradictions between worker findings
2. Score each contradiction: resolvable (more research needed) or irresolvable (genuine ambiguity)
3. Flag which findings are weak (single source, low confidence)
4. Do NOT resolve contradictions — only surface them
</task>
<output_format>
{
  "status": "success",
  "contradictions": [
    {
      "between": ["W1.finding_id", "W2.finding_id"],
      "description": "...",
      "type": "resolvable | irresolvable | scope_overlap",
      "resolution_needed": "what additional research would resolve"
    }
  ],
  "weak_findings": [{ "worker_id": "W1", "finding": "...", "reason": "single source" }],
  "ready_for_synthesis": true
}
</output_format>
```

If `ready_for_synthesis: false` → identify which worker needs another pass. Loop back.

---

## Phase 3 — Orchestrator: Synthesis (Superposition → Collapse)

**Model**: Claude Sonnet / Opus

This is the Coconut moment: hold all findings in superposition, then collapse to the most evidence-supported synthesis. Do NOT collapse prematurely.

```xml
<role>
You are a senior researcher synthesizing multi-source findings into a coherent picture.
You hold contradictions openly — you don't flatten them into false consensus.
</role>
<context>
Research question: [QUESTION]
All worker findings: [research-state.json.worker_findings]
Contradictions: [consensus-check output]
</context>
<task>
Synthesize all findings into a coherent answer to the research question.
</task>
<think_before_answering>
Step 1: List all plausible synthesis narratives (≥3).
Step 2: For each narrative, score on: evidence_support (0–1), internal_consistency (0–1), predictive_power (0–1).
Step 3: Select highest-scoring narrative.
Step 4: Explicitly state what the other narratives explain better.
This is the superposition collapse. Don't skip it.
</think_before_answering>
<constraints>
  <required>
    - All contradictions acknowledged in synthesis
    - Confidence rated per insight, not overall
    - Open questions explicitly listed
    - "I don't know" where evidence is insufficient
  </required>
  <forbidden>
    - False consensus (pretending contradiction doesn't exist)
    - Dropping a finding because it's inconvenient
    - Confidence > evidence
  </forbidden>
</constraints>
<output_format>
{
  "status": "success",
  "data": {
    "question": "...",
    "key_insights": [
      {
        "insight": "...",
        "confidence": 0.0,
        "supporting_workers": ["W1", "W2"],
        "contradicted_by": []
      }
    ],
    "synthesis_narrative": "3–5 sentence coherent answer",
    "mode_specific": {
      "mk": {
        "mk_hypothesis": "...",
        "p1p": { "a": "...", "b": "...", "incompatibility": "..." },
        "nto": "...",
        "mk_level": "МК₁"
      }
    },
    "acknowledged_contradictions": [],
    "open_questions": [],
    "confidence_overall": 0.0,
    "next_steps": []
  },
  "hypotheses": [
    { "id": "h1", "narrative": "...", "score": 0.0 },
    { "id": "h2", "narrative": "...", "score": 0.0 },
    { "id": "h3", "narrative": "...", "score": 0.0 }
  ],
  "selected_hypothesis": "h1",
  "next_action": "Run /judge to validate synthesis, or proceed to /grill-with-docs"
}
</output_format>
<critical_reminder>
Do not collapse superposition before scoring ≥3 narratives. Contradictions must be acknowledged.
</critical_reminder>
```

---

## Phase 4 — Judge: Validation

Isolated evaluator context. See `/judge` skill.

Criteria for research validation:
- `r-question-answered`: synthesis directly answers the original question
- `r-evidence-grounded`: every key insight has ≥1 evidence point
- `r-contradictions-handled`: no contradiction silently dropped
- `r-confidence-calibrated`: confidence scores match evidence quality
- `r-open-questions-honest`: gaps stated, not hidden

---

## State schema (`research-state.json`)

```json
{
  "version": 2,
  "question": "...",
  "mode": "mk | market | technical | user | domain | custom",
  "phase": "distortion-check | decompose | research | consensus | synthesis | validation | done",
  "distortions_found": [],
  "clarified_question": "...",
  "assumptions_to_validate": [],
  "workers": [],
  "worker_findings": {},
  "contradictions": [],
  "synthesis": null,
  "judge_report": null,
  "open_questions": [],
  "updated_at": ""
}
```

---

## After research

**If mode = mk**: update `value_proposition_mk.md` sections 2–3 from synthesis output.
**If mode = market/domain**: create `docs/research-report.md` + `CONTEXT.md` entries.
**Always**: run `/judge` on synthesis before using it as input to `/contract` or `/grill-with-docs`.
