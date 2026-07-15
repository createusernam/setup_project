---
name: researcher
description: "Evidence acquisition and validation for open questions: search, multi-angle or single-agent research, contradiction handling, synthesis, confidence, and judge validation. Always outputs canonical `research-state.json`; produces a verification-first `research-report.md` when the selected mode or user request requires a human-readable report. Use when users ask to research, investigate, verify, discover, analyze a market, assess technical feasibility, or fill factual gaps. Responsibility boundary: does not turn validated findings into a teaching/decision guide and does not render PDF; hand those outputs to `research-to-guide`, then `guide-pdf`."
---

# /researcher — Multi-Agent Research Flow

General-purpose research skill. Multiple agents explore in parallel, reach consensus, synthesize.

General-purpose across domains — market research, technical feasibility, competitive analysis, user behavior, domain knowledge, any open question. Domain-specific applications extend it via `--mode custom` rather than a dedicated mode.

**Cost posture**: free-first by default. Retrieval ladder starts with local/no-API-key tools; paid APIs only on explicit user request. Research cache with TTL avoids repeat searches. Bounded swarm size — many agents are for context-hygiene and broad sampling, not quality-through-quantity.

## Usage

```
/researcher [--mode market|technical|user|domain|custom]
            [--question "research question"]
            [--angles "angle1, angle2, angle3"]
            [--context "relevant background"]
            [--baseline <path>]   # additive mode: research EXTENDS an existing doc
```

**Mode descriptions:**

| Mode | Purpose | Worker types |
|---|---|---|
| `market` | Market landscape, sizing, competitors | domain + competitive |
| `technical` | Technical feasibility, tools, approaches | technical |
| `user` | User behavior, pain points, workarounds | user-behavior |
| `domain` | Domain knowledge, concepts, terminology | domain |
| `custom` | Free-form: user specifies angles and worker types explicitly | as specified in `--angles` |

Without args: orchestrator decomposes the question automatically, infers mode from the question semantics.
With `--baseline`: additive mode — synthesis is scored against the baseline doc and the deliverable is an **edit-plan**, not a fresh report. See *Additive mode* below.

## Output

`docs/research-state.json` — shared state across all phases (with `phase` field for session resume)
`docs/research-report.md` — optional verification-first synthesis for modes or requests that require a human-readable report
`docs/.research-cache/` — search result cache (TTL-based, avoids repeat searches)

### Session resume

If a research session is interrupted, a fresh session can resume:
1. Read `docs/research-state.json` — check `phase` field
2. Read `.research-cache/` — skip already-done searches
3. Reconstruct worker state from `worker_findings` and `findings_timeline`
4. Continue from the current phase
5. If resuming Phase 1 with partial workers: re-launch only incomplete workers (completed workers are already in state)

The `phase` field gates which phases have been completed. A state machine pattern: each phase transition writes the new phase before executing, so a mid-phase crash is detectable (phase = "research" but workers incomplete → re-launch).

## Architecture

```
[INTAKE] Clarify intent with user (Phase -2)
    ↓
[METAMODEL] Clean distortions (Phase -1)
    ↓
[DECOMPOSE] → Plan angles → PLAN-CONFIRM (Phase 0)
    ↓
[PROBE] Cheap landscape scan — validate angles (Phase 0.5) ← loop back to Decompose if missing
    ↓
[WORKER-1] [WORKER-2] ... [WORKER-N]  ← parallel (Claude Code) or sequential (OpenCode)
    ↓   Each worker: Screener → Searcher → Extractor → (optional: Verifier × N)
[ORCHESTRATOR] Consensus check → Collusion detection → Synthesis (superposition → collapse) (Phase 2–3)
    ↓
[JUDGE] Cross-model panel → Weighted rubric → Adversarial verification → Verdict (Phase 4)
```

**State-First**: all phases read/write `research-state.json`. Each worker produces next state, not events. Phase field in state enables session resume — a fresh session reads state, discovers phase, and continues.

## Retrieval Infrastructure

Retrieval quality is ~70% of research success. The search layer is first-class, not assumed.

### Retrieval ladder (no-API-key first)

Try each level in order; skip to next if unavailable:

1. **Local SearXNG** (Docker, `?format=json`) — primary. Disable news/general categories, enable arxiv and technical sources. Multi-page deep sampling (don't trust page 1 — it's often SEO-spam). If SearXNG is not installed or not running → skip to DuckDuckGo (step 2). First-time setup: `docker run -d -p 8080:8080 searxng/searxng`.
2. **DuckDuckGo** — fallback for broad web. Available via `WebFetch` without API key.
3. **Playwright headless** — for sites blocking WebFetch (Reddit, paywalled abstracts, JS-rendered pages). Requires Playwright MCP or `npx playwright`.
4. **Tavily free / direct APIs** (arxiv, Semantic Scholar) — only when explicitly needed or when 1–3 are unavailable.

### Search result cache

Key = hash of normalized query. TTL = n days (configurable, default 3). Cache lives in `docs/.research-cache/`. Before any search, check cache. Mandatory for repeat research sessions.

### Deep-sampling rule

SearXNG page 1 is SEO-heavy. Sample pages 1–5, deduplicate by domain+title. The reason for many parallel workers is **broad sampling past the SEO layer** — not "more agents = better quality." Worker count is a sampling-width tactic, not a quality lever.

### Retrieval budget

Per-worker: max N queries, max depth = M pages. Budget is set in Phase 0 plan and enforced. Prevents cost runaway.

## Execution by runtime

See `docs/agent/COMPAT.md` for full cross-model guide.

**Agent-native runtime**: phases may run as parallel agent calls. Resolve orchestration through
`reasoning_balanced`, workers through `research_worker`, and validation through `review_acceptance`.

**General coding runtime**: parallel workers use the runtime's subagent primitive. Orchestrator and
worker model IDs come from runtime settings and project `model-bindings.json`, not this prompt.

**Example runtime mapping** (replace with user-configured provider/model IDs):

```jsonc
{
  "model": "provider/reasoning-model-id",
  "small_model": "provider/research-worker-model-id"
}
```

Keep runtime settings consistent with `model-bindings.json`; worker and acceptance roles may require
separate per-call or runtime overrides.

**Terminal**: human orchestrates. Each phase = separate LLM call. Copy JSON between calls.

### One agent or many? — complexity-based routing

The full multi-agent flow pays off only for large, multi-angle questions where breadth needs isolation. Use this decision table:

| Question profile | Worker count | Mode |
|---|---|---|
| <3 independent angles, narrow scope | 0 (inline) | Single agent: metamodel → research → synthesis in one context |
| 3–5 angles, comparative | 3–5 workers | Parallel workers + consensus |
| 5–8 angles, broad landscape | 5–8 workers | Full multi-phase flow |
| Strategic / top-level concept | Human-orchestrated | More waypoints, explicit gates at every phase |

FF-transformers excel at execution-level research but struggle with top-level strategic concepts — route accordingly. The orchestration overhead isn't worth it for narrow questions. Reserve parallel workers for genuine breadth, not as a default.

Whichever you pick: pass the belief-state in the prompt, don't inherit a huge context (semantic-freeze risk). Many agents are a tactic for **context-hygiene** (fresh windows, no semantic-freeze) and **broad sampling** (past search-engine SEO-spam), NOT for quality-through-quantity.

---

## Phase -2 — Intake Dialogue

**Goal**: clarify the research intent before any decomposition. Raw research questions arrive as incomplete, internally contradictory narratives. A brief clarifying dialogue surfaces hidden context and tests mutual understanding.

**Capability profile**: `reasoning_balanced`

**When to run**: always when the research question comes from a human (not from another agent/skill). Skip for programmatic calls where the question is already structured.

**What to ask** (3–6 questions, pick the relevant subset):

1. **Freshness**: how recent must sources be? (last month / last year / no constraint)
2. **Scope boundary**: what specifically are we NOT researching? (reduces worker drift)
3. **Must-cover angles**: any specific facets the user already knows they need?
4. **Definition of done**: what does "good enough" look like? (a ranked list? a report? a single answer?)
5. **Budget/width**: quick narrow answer or broad landscape scan?
6. **Domain volatility**: is this a stable domain (regulated, slow-changing) or volatile (fast-moving tech)? Affects iteration depth.

Output: update `research-state.json.intake` with clarified intent, scope boundaries, and DoD. Then proceed to Phase -1 with the clarified question.

---

## Phase -1 — Metamodel Distortion Check

**Goal**: clean the research question before decomposing it. Distortions in the question propagate into all downstream findings.

**Capability profile**: `reasoning_balanced`

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
| **False dichotomy** | "X or Y", "should we A or B" | Is the either/or real, or does it hide a third+ option? |

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

**Capability profile**: `reasoning_balanced`

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
Execution context: [CLAUDE_CODE | OPENCODE | TERMINAL]
Retrieval budget: [max queries per worker, max depth pages]
</context>
<task>
1. Assess question complexity: narrow (3 angles) / comparative (3–5 angles) / broad landscape (5–8 angles)
2. Identify N distinct research angles — adaptive count based on question breadth, not capped at 5
3. For each angle: define scope, worker type, expected output format, explicit "out of scope" boundaries
4. Identify what each worker needs from others (dependencies)
5. Produce PLAN-CONFIRM with Mermaid visualization of the angle decomposition for human approval
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
    "complexity": "narrow | comparative | landscape",
    "worker_count": 3,
    "workers": [
      {
        "id": "W1",
        "angle": "domain-landscape",
        "sub_question": "...",
        "scope": "...",
        "out_of_scope": ["what this worker explicitly does NOT research"],
        "worker_type": "domain | user | technical | competitive",
        "capability_profile": "research_worker | reasoning_balanced",
        "depends_on": [],
        "expected_output": "...",
        "retrieval_budget": {"max_queries": 10, "max_depth": 5}
      }
    ],
    "plan_summary": "3-sentence plan description",
    "plan_mermaid": "mermaid flowchart of angle decomposition for human bird's-eye validation"
  },
  "hypotheses": [],
  "selected_hypothesis": "",
  "next_action": "Type APPROVE to launch probe, or describe changes"
}
</output_format>
<critical_reminder>
Sub-questions must be non-overlapping and each independently researchable. Each worker must have explicit out_of_scope boundaries. Output valid JSON only; include a Mermaid diagram so the human can visually validate coverage and gaps.
</critical_reminder>
```

**After APPROVE**: write initial `research-state.json`, proceed to Phase 0.5 (Probe).

---

## Phase 0.5 — Probe (Cheap Landscape Scan)

**Goal**: validate decomposition angles with a quick, cheap scan before committing to full research. This is a cheap insurance policy — catches missing angles and dead ends before launching expensive workers.

**Capability profile**: `research_worker`

**What it does**:
1. Run 1–2 surface-level searches per proposed angle
2. Check: does this angle have enough substance to justify a full worker?
3. Does the scan reveal any angle that was missed in decomposition?
4. Are any proposed angles dead ends (no results, or entirely off-topic)?

**Output**: update `research-state.json.probe_results`. If the probe reveals a missing angle or a dead end, return to Phase 0 to adjust the decomposition. If all angles check out, confirm with user and proceed to Phase 1.

Skip for: single-angle inline research, programmatic calls, or when the user explicitly says "just go."

---

## Phase 1 — Workers: Parallel Research

Each worker receives:
- Their specific sub-question
- Current `research-state.json`
- Their worker type prompt (below)

**Model routing**: use `research_worker` for bounded desk research and `reasoning_balanced` for
synthesis-heavy angles. Match capability to complexity; weaker/cheaper bindings need narrower,
more explicit sub-questions.

### Functional split (optional, for deep research)

When an angle requires high factual precision, split the worker into a 3-stage sub-pipeline:

1. **Searcher** — broad search, collects candidate URLs/sources (breadth, low precision OK)
2. **Extractor** — reads top sources, pulls falsifiable claims with exact citations
3. **Verifier** — attempts to *falsify* each claim independently; claims surviving ≥2 verifiers graduate to findings

Use this for angles where accuracy is critical (medical, legal, factual claims). Skip for exploratory/opinion-gathering angles.

### Pre-filter (Screener)

Before deep processing, run a cheap-model Screener on raw search results: discard obviously off-topic/low-authority hits, deduplicate by domain+title, keep only relevant items. This cuts junk before it enters the worker's context window — saves tokens and prevents distraction.

### Adversary check (optional)

For critical claims: run 3 independent SearXNG searches per claim with different query formulations, then majority-vote. If all 3 searches surface conflicting information, flag the claim as `contested` with the conflict described. This is a lightweight adversarial layer — the full adversarial verification lives in Phase 4.

### Worker failure-claim protocol

When a worker reports "not found / not possible / not reachable", the orchestrator must NOT accept this as DONE. Before accepting a failure claim, verify:
1. Target restated (what exactly was sought)
2. Actual count vs target (how many of N sources found)
3. Methods tried with evidence (which queries, databases, tools)
4. Solution space coverage estimate (what fraction of possible sources was explored)
5. Untried method classes (what different approaches remain)
6. Proposed next method that changes data source / query strategy / tool

Unless ≥3 genuinely different method classes have failed, mark as PARTIAL and re-launch a different-method worker slice.

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

**competitive** worker:
- Who else is solving this
- Their approach and its gaps
- What they avoid and why

---

## Phase 2 — Orchestrator: Consensus Check

Before synthesis, identify contradictions and collusion across workers. Orchestrator role.

**Capability profile**: `reasoning_balanced`

**Multi-stage consensus** (for ≥5 workers):
1. Raw findings → initial clustering by topic
2. Contradiction surfacing (explicit disagreements)
3. **Collusion check** (silent agreement is also a risk)
4. Consensus voting (where evidence allows)
5. Final synthesis input

### Collusion detection

When all workers agree on a finding, the consensus step must explicitly ask: *"Could this be a shared blind spot? Are all workers from the same model family? Is there a known counterposition?"* Same-architecture models can converge on shared errors. Triangulation across distinct configured model families can reveal them. Flag unanimously-agreed findings as `collusion_risk: medium` if all workers share one model architecture.

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

**Capability profile**: `reasoning_balanced`

This is the Coconut moment: hold all findings in superposition, then collapse to the most evidence-supported synthesis. Do NOT collapse prematurely.

**Anti-Captain-Obvious guard**: LLMs default to statistically-common "best practice" answers from pretraining. Before collapsing, the orchestrator must force a GRM-style scoring pass: generate evaluation Principles → assign Weight (1–10) → Score each narrative (1–10) against principles. This structured deliberation prevents collapsing to the shallow first plausible answer. The scoring must happen BEFORE selecting a narrative, not as post-hoc justification.

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
    - Filtering options by the decision-maker's fit/constraints — that's a separate step after synthesis, never during
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
    "mode_specific": {},
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
  "next_action": "Type APPROVE to proceed to Phase 4 (validated by researcher's built-in weighted-rubric judge; the standalone /judge skill is for product-development artifacts — plan, contract, feature, design — not research synthesis)"
}
</output_format>
<critical_reminder>
Do not collapse superposition before scoring ≥3 narratives. Contradictions must be acknowledged.
</critical_reminder>
```

### Synthesis scaffold — for a long, shareable synthesis (optional)

When the synthesis will become a human-readable research report (not just a state file), fill a fixed 6-section scaffold instead of a free-form narrative. It forces completeness — you can't quietly skip a contradiction or drop the question-bank. This is a verification-first report contract, not a teaching-guide composition system.

1. **Convergence** — what all/most workers agree on (the load-bearing findings).
2. **Complementarity** — where workers cover different facets that compose into one picture.
3. **Contradictions** — every unresolved disagreement, carried openly (never flattened into false consensus).
4. **Gap-map** — what the question still doesn't answer. In additive mode this is baseline-covered vs genuinely NEW (see *Additive mode*).
5. **Question inventory** — the open questions consolidated and ranked by what to resolve first.
6. **Recommended additions** — concrete next moves / sections to write. In additive mode this becomes the edit-plan.

Sections 4 and 6 are lightweight in from-scratch research and load-bearing in additive mode.

---

## Optional — Ranking for a decision (after synthesis, before validation)

**Capability profile**: `reasoning_balanced`

**Apply when**: the output is a *set of options* someone must choose among (market/niche options, delivery models, tech choices, strategies) AND there is a decision-maker with real constraints.
**Skip when**: the research answers a factual or causal question ("why did X fail", "how does Y work") — there is nothing to rank.

Ranking runs *after* synthesis and never feeds back into it — the research stays on-merits (see the decision-lens rule in Phase 3).

Rules:
- **RANK, not ELIMINATE.** Keep every option from synthesis; order them for the decision-maker, never silently drop one.
- **Barriers get a gateway, not a ⛔.** An option that is hard for this decision-maker is marked ⚠️ + a concrete gateway (what to learn / build / access to enter it) so it stays on the map as a "later" path.
- **Weights come from the decision's real constraints**, applied ONLY here. Derive them from what actually binds: cash urgency → weight time-to-value; solo operator → weight low-maintenance / scalability; regulated buyer → weight compliance. Equal weights are an anti-pattern — they let high-attractiveness / zero-fit options win.
- **Every option carries a key figure** (size / money / effort) with a source.

Output: append `ranking` to state — a ranked list of ALL options with score, key figure, and (for barriered options) the gateway.

---

## Additive mode (`--baseline <path>`) — extend a doc instead of writing a new one

**Apply when**: the research must *grow an existing deliverable* (a v3 → v4 textbook, a doc that already covers most of the ground) rather than start from a blank page.
**Skip when**: there is no prior artifact — run the normal flow.

Additive mode changes three things:

- **Gap-map step (in synthesis).** Before writing anything, build a table of the baseline against the findings — *what the baseline already covers* vs *what is genuinely NEW*. Synthesis is scored against this map, so you never re-derive content the baseline already has.
- **Edit-plan output, not a narrative.** The deliverable is a numbered list of edits — `{section, what to add, rationale}` — keyed to the baseline's structure, not a fresh report. Each edit states where it lands and why the baseline needs it.
- **Judge criterion `r-false-newness` (see Phase 4).** The judge checks every "NEW" claim against the baseline and rejects anything already present under a different name — e.g. flagging "belief-state" as new when the baseline already had "semantic-freeze."

State gains `baseline`, `gap_map`, and `edit_plan` fields.

---

## Phase 4 — Judge: Validation

Isolated evaluator context. For high-stakes research, bind a panel of at least two distinct model
families/IDs; concrete selections come from user configuration. Single-family review can share blind spots.

The judge evaluates on two independent axes:
- **Verification** (process): did we follow the method? Are findings properly sourced and contradictions handled?
- **Validation** (outcome): did we actually answer the real question? Is the synthesis actionable?

A methodologically perfect study can still miss the point — score both axes separately.

### Weighted rubric (GRM-native format)

Use Principle × Weight × Score decomposition. The judge generates evaluation principles, assigns weight 1–10, then scores 1–10 against each. This structured format reactivates embedded evaluator expertise from RL training and produces diagnostic scores (not just a single number).

Each criterion is decomposed into 3–5 atomic yes/no sub-questions (BINEVAL pattern), evaluated independently, then combined into a multidimensional score with a diagnostic trace of what failed and why.

### Evaluation criteria

| Criterion | Weight | Description |
|---|---|---|
| `r-question-answered` | 10 | Synthesis directly answers the original (clarified) question |
| `r-evidence-grounded` | 10 | Every key insight has ≥1 evidence point with source |
| `r-contradictions-handled` | 8 | No contradiction silently dropped; collusion acknowledged |
| `r-confidence-calibrated` | 7 | Confidence scores match evidence quality; no overconfidence |
| `r-open-questions-honest` | 6 | Gaps stated, not hidden; known-unknowns listed |
| `r-not-obvious` | 8 | Would any competent LLM produce this finding from the question alone, without the research phase? If yes → flag as shallow |
| `r-criticism-grounded` | 5 | Each critique cites a specific fact from findings, not a general principle; LLM "fake criticism" that sounds valid but misses real problems is rejected |
| `r-false-newness` *(additive only)* | 8 | No "NEW" claim duplicates baseline content under a different name |
| `r-insufficient-premises` | 5 | Flags when input data is fundamentally incomplete/contradictory — the judge must say "cannot validate from these premises" rather than validating broken foundations |

### Per-claim adversarial verification (for high-stakes research)

For critical claims: ≥2 independent verifiers attempt to *falsify* each claim (not confirm). Claims surviving all verifiers graduate. Use the 5-searchers → 15-extractors → 3-verifiers-per-claim pipeline pattern. This is adversarial — the verifier's task is to find counterevidence, not to rubber-stamp.

### Verdict

Scores are on the Principle × Weight × Score scale (each criterion: weight 1–10 × score 1–10 → max 100). Normalize to 0.0–1.0 before comparing against thresholds:

- **PASS** (all must_pass ≥ 0.70 on the normalized scale, i.e. ≥ 70% of max weighted score): proceed to use synthesis
- **CONDITIONAL**: fix listed issues, re-run judge. Common conditions: shallow findings (r-not-obvious fail), ungrounded critique (r-criticism-grounded fail), insufficient premises (cannot validate)
- **FAIL** (must_pass < 0.70 or r-insufficient-premises triggered): return to research phase, refine angles

### Intent visualization checkpoint

Before the judge runs, the synthesis must include a visual/intent summary (Mermaid diagram, structured What-I-Thinks-You-Mean block, or pseudographic) so the human can rapidly verify that the model's understanding matches the question's intent. LLM prose is always "correct" within the model's own interpretive bubble — the visual checkpoint catches misinterpretation before validation. This diagram verifies research intent; it does not prescribe the final guide's visual style.

---

## State schema (`research-state.json`)

```json
{
  "version": 3,
  "question": "...",
  "mode": "market | technical | user | domain | custom",
  "phase": "intake | distortion-check | probe | decompose | research | consensus | synthesis | validation | done",
  "intake": {
    "clarified_intent": "...",
    "scope_boundaries": "...",
    "definition_of_done": "...",
    "freshness": "last-month | last-year | no-constraint",
    "domain_volatility": "stable | volatile",
    "budget_width": "narrow | landscape"
  },
  "distortions_found": [],
  "clarified_question": "...",
  "assumptions_to_validate": [],
  "probe_results": {},
  "workers": [],
  "worker_findings": {},
  "contradictions": [],
  "collusion_flags": [],
  "synthesis": null,
  "ranking": null,
  "baseline": null,
  "gap_map": null,
  "edit_plan": null,
  "judge_report": null,
  "memory_policy": {
    "cache_ttl_days": 3,
    "findings_persist": true,
    "ephemeral_after_done": false
  },
  "retrieval_budget": {
    "max_queries_per_worker": 10,
    "max_depth_pages": 5
  },
  "findings_timeline": [],
  "open_questions": [],
  "updated_at": ""
}
```

---

## After research

**If mode = market/domain**: create `docs/research-report.md` + `CONTEXT.md` entries.
**Always**: Phase 4 (researcher's built-in judge) is the validation gate. The research-specific weighted rubric (r-question-answered, r-evidence-grounded, etc.) lives here. The standalone `/judge` skill (product-brief, contract, plan, feature, design) is for product-development artifacts — not research synthesis.

**If the user requests a practical, teaching, decision, or user-facing guide**: finish validation first, then hand the baseline and validated report to `/research-to-guide`. Researcher protects the evidence; research-to-guide changes the reader journey and writes a separate Markdown deliverable. Do not improvise this transformation inside synthesis: it needs a preservation ledger and a second coverage audit. If PDF is requested, render the finished Markdown afterward with `/guide-pdf`; never let rendering alter research content.

## Anti-patterns

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| **Parallel workers for narrow question** | Orchestration overhead > research value; workers search in circles with nothing to find. Worker count is a sampling-width tactic, not a quality lever. | Use inline single-agent flow for <3 independent angles. |
| **Accepting "not found" without verification** | Workers default to "not found" when the search tool is weak or query phrasing is off — not when information genuinely doesn't exist. | Apply the 6-point failure-claim protocol before accepting. |
| **Collapsing superposition to first plausible answer** | LLMs default to statistically-common best-practice answers regardless of evidence. The first coherent synthesis feels right but is often uncritical. | Force GRM scoring pass (Principles → Weights → Scores) *before* narrative selection. |
| **Single-model judging** | Same-architecture judge shares the synthesis model's blind spots; colludes silently on shared errors. | Minimum 2 model families in judge panel. |
| **Mixing agent phases from different research sessions** | Each worker run has its own context window and information horizon; mixing workers from session A with workers from session B creates internal inconsistency. | Use `phase` field in state to detect session boundaries; if workers are from a different session, re-run Phase 1 cleanly. |
| **Skipping intake for complex questions** | Raw research questions contain unstated assumptions, scope conflicts, and hidden budget constraints. Without intake dialogue, workers research the wrong question. | Always run Phase -2 when the question comes from a human (not another agent). |
| **Cache blindness** | Skipping search cache for "freshness" when the same query was run 2 hours ago burns tokens and time. | Check `.research-cache/` before every search; TTL handles staleness. |

---

## Deliverable responsibility boundary

The human-readable output of this skill is a **verification-first research report**. Its structure exposes convergence, complementarity, contradictions, gaps, open questions, confidence, and recommended additions.

Do not apply mentor, field-textbook, opportunity-map, or decision-guide prose patterns inside research synthesis. Those patterns belong to `/research-to-guide`, after Phase 4 validates the evidence. PDF typography, page layout, and print rendering belong to `/guide-pdf`, after the final Markdown exists.

`RESEARCH_HANDOFF`:

```yaml
evidence_owner: researcher
validated_report: docs/research-report.md | null
state: docs/research-state.json
reader_composition: research-to-guide
print_rendering: guide-pdf
uncertain_about: []
```
