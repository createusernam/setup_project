# Architecture Guide — the Architect phase runs on a clean prompt

Where the **hardest architecture reasoning** runs, and why it leaves the agent harness. Governs *how* you execute PHASE 2 (`/planning-with-files`) and PHASE 2b (`/grace-plan`) in `PIPELINE.md` — those skills define the **artifacts**; this guide defines the **surface** the reasoning happens on. The gates (PM validation, `/judge` plan) do not move — only the reasoning surface does.

**A human runs this by hand.** In: `product_brief.md` (+ `CONTEXT.md`, `docs/adr/`). Out: GRACE architecture artifacts that re-enter at the PM gate. The by-hand procedure — inputs/outputs per step, a copy-paste prompt, and the acceptance checklist — is the **Runbook** immediately below; the sections after it explain *why* each step is shaped that way.

> Doing it? Jump to the Runbook. Want the reasoning? Read Why → Rules first.

## Runbook — how a human executes this

One clean-room chat session, then re-entry into the pipeline. Inputs and outputs are fixed at each step.

**Inputs (open these before you start):**
- `product_brief.md` (status: pm-approved) — WHAT/WHY, esp. §7 user journey and §8 success criteria
- `CONTEXT.md` + `docs/adr/` (from `/grill-with-docs`) — domain glossary + decisions already locked
- Stack: from `product_brief` / `CONTEXT.md` / `docs/adr/` (fixed technology choices). Note: `docs/technology.xml` does not exist yet — `grace-init` writes it at Phase 2b, AFTER this phase. If a `technology.xml` already exists from a prior GRACE-Full project, use it; otherwise the stack facts come from CONTEXT/ADR.
- `business_model.md` (if your discovery process produced one) — business info: segment, value, arguments. The architecture must serve this, not just the brief.
- The single architecture question this session must settle

**Outputs (what you leave with):**
- Emit GRACE artifacts (`docs/development-plan.xml`, `docs/knowledge-graph.xml`) if GRACE-Full is also triggered; otherwise emit the `task_plan.md` architecture section only.
- `docs/adr/NNN-*.md` — one ADR per non-obvious decision (incl. rejected options)
- A PASS through the acceptance checklist, then `pm-review.json` APPROVE + `/judge` PASS

### Steps

| # | Step | In | Out |
|---|---|---|---|
| 0 | **Gate check** — confirm ≥2 conditions from *When to leave the agent* | that table | go / no-go (no-go → stay in `/planning-with-files`) |
| 1 | **Pick surface** — Rule 2, by data-sensitivity + availability | Rule 2 table | chosen surface (AI Studio / API / self-host / DeepSeek) |
| 2 | **Load system prompt** — fill the Architect prompt below with project specifics | template + `CONTEXT.md` glossary, stack, ADR titles | session seeded with YOUR Belief State |
| 3 | **Send task** — paste the task message (use-cases + input artifacts) | `product_brief` §1/§7/§8, glossary | model returns **PLAN_CONFIRM** (its understanding + ≥3 approaches) |
| 4 | **Align** — read PLAN_CONFIRM, correct misreadings, type `APPROVE` only when it matches intent | PLAN_CONFIRM | agreed understanding — *this is where you согласовать before it spends effort* |
| 5 | **Drive superposition** — make it score ≥3 architectures, collapse only at SYNTHESIS_GATE | approved plan | scored hypotheses + selected architecture + rationale |
| 6 | **Collect artifacts** — it emits GRACE XML + ADRs as paste-ready blocks | selected architecture | `development-plan.xml`, `knowledge-graph.xml`, ADRs |
| 7 | **Reconcile** — run the acceptance checklist; iterate in-session on any fail | artifacts + checklist | accepted artifacts |
| 8 | **Re-enter** — save files into the repo; run the pipeline gates | accepted artifacts | `pm-review.json` APPROVE → `/judge` PASS → Visualize → `/to-issues` |

> **Where the prompt goes:** on surfaces with a **system field** (API, AI Studio) paste it there and the artifacts in the first user turn. In a **plain chat** (DeepSeek) paste the whole block as message 1, then the task as message 2.

### The Architect system prompt (copy, fill `{{…}}`)

```xml
<role>
You are a staff-level software architect with deep domain and distributed-systems
experience. Your belief: the best architecture is the one that survives the real
use-cases and edge cases with the least coupling — not the most familiar pattern.
</role>

<belief_state>
Project: {{name}} — {{one line: what it is}}
Stack (fixed): {{languages, frameworks, datastore}}
Domain language (use these exact terms): {{glossary from CONTEXT.md}}
Decisions already locked (do not relitigate): {{ADR titles / constraints}}
What exists today: {{greenfield | modules that already exist}}
Business model (optional, if business_model.md exists): {{who/value/arguments — blocks 1,2,8,9}}
</belief_state>

<goal>
GOAL_ROOT: {{the one architecture decision this session must settle, one sentence}}
Success: a module breakdown that covers every use-case below, minimises coupling,
  can be verified, and uses the domain language above.
Not success: a generic layered diagram that ignores the use-cases; invented
  vocabulary; picking a pattern before scoring alternatives.
</goal>

<use_cases>
{{paste the 2–5 critical use-cases / journeys from product_brief §7}}
</use_cases>

<guide>
Classify each module: ENTRY_POINT | CORE_LOGIC | DATA_LAYER | UI_COMPONENT | UTILITY | INTEGRATION.
Prefer composition over inheritance; explicit data flows; contracts before code.
If a requirement is ambiguous or missing: STOP and ask — do not invent it.
</guide>

<plan_confirm>
Before designing: restate GOAL_ROOT in your words, list your assumptions, and list
the ≥3 architectures you will compare. Output status "needs_approval" and WAIT for
me to type APPROVE before producing the full design. Marker: PLAN_CONFIRM
</plan_confirm>

<think_before_answering>
Step 1: enumerate ≥3 distinct architectures (different module boundaries / data flows).
Step 2: score each 0.0–1.0 on use-case coverage, coupling, verifiability, fit-to-stack.
Step 3: only now select the highest — do not collapse earlier. Marker: SYNTHESIS_GATE
Step 4: state what each rejected option would have been better at.
</think_before_answering>

<output_format>
After APPROVE, produce in this order:
1. HYPOTHESES — JSON: [{id, description, score, evidence[]}] + selected_hypothesis
2. MODULE TABLE — M-xxx | name | type | purpose | depends | source path | test path | V-M-xxx
3. DATA FLOWS — DF-xxx: modules involved, data carried, where it can break
4. WALKTHROUGH — trace 2–3 use-cases module by module; flag any circular dependency
5. ARTIFACTS — paste-ready fenced blocks:
   docs/development-plan.xml · docs/knowledge-graph.xml · docs/adr/NNN-*.md
Every module carries a MODULE_CONTRACT (PURPOSE / SCOPE / DEPENDS). Output NO code.
</output_format>

<critical_reminder>
PLAN_CONFIRM before designing. SYNTHESIS_GATE before selecting one architecture.
Use ONLY the domain language above. Ask if a requirement is missing — never invent it.
</critical_reminder>
```

### Task message (first user turn)

```
Here are the inputs. Do NOT design yet — start with PLAN_CONFIRM.

PRODUCT BRIEF (intent + journey + success):
{{paste product_brief §1, §7, §8}}

DOMAIN GLOSSARY (use these terms exactly):
{{paste glossary from CONTEXT.md}}

LOCKED DECISIONS:
{{paste relevant ADR one-liners}}

BUSINESS MODEL (who/value/arguments): {{paste business_model.md blocks 1,2,8,9 if present}}

THE DECISION THIS SESSION MUST SETTLE:
{{the specific architecture question}}
```

### Acceptance checklist — reconcile before re-entry (*согласовать результат*)

Re-enter the pipeline only when every box is checked. Any fail → fix it **in the same session** (a pointed instruction or a few-shot example — never token-by-token micromanagement).

- [ ] ≥3 architectures were scored before one was selected (superposition visible, not a single answer)
- [ ] Every module has a MODULE_CONTRACT (PURPOSE / SCOPE / DEPENDS)
- [ ] Every module traces to ≥1 use-case, and every use-case from §7 is covered
- [ ] DF-xxx data flows defined for the critical use-cases
- [ ] Walkthrough done; no circular dependencies
- [ ] Domain terms match `CONTEXT.md` — no invented vocabulary
- [ ] `verification-ref` (V-M-xxx) present for significant modules (GRACE Full)
- [ ] Artifacts are well-formed and paste into the repo without rework

Only then: save the artifacts and run PHASE 2-PM (PM agent, **different model**) + `/judge` plan. Those two gates — not this chat — are the final sign-off.

---

## Why (the reasoning this unlocks)

The principle: designing architecture takes **very low-level control over the model** — the aim is to pull its deep knowledge to the surface, not the first safe answer it defaults to. That only works when the system prompt is pared back to almost nothing, leaving your own technique as the single force bending the trajectory. Run the same model inside an agent and its raw reasoning ceiling never fully shows. Of the hosted options the least-cluttered are Google AI Studio (shipped deliberately empty) and DeepSeek's chat, whose prompt is barely more than a line or two on safety.

The mechanism, in the setup's own terms (`../agent/PROMPT-FORMAT.md` **L5**): the system prompt does not give instructions — it **constructs the Belief State** (what the model believes is true about its role and world), and it sits at the **top of context = the highest-attention position**. An agent harness (Claude Code, OpenCode, Cursor, Copilot) puts *thousands* of tokens of tool-use scaffolding, output-formatting, and safety framing in exactly that slot. That is a **generic agent Belief State**, not your architecture Belief State — and it is the first thing every subsequent token attends to.

- For **code execution** that scaffolding is a feature — you *want* tool discipline, patch etiquette, refusal to hand-wave.
- For **architecture reasoning** it is a tax: the trajectory is anchored to "diligent tool-using assistant" before you ever state the problem. The one phase where you want maximum unconstrained reasoning is the one phase where you should own every token of the system prompt.

So for hard architecture, **strip the harness to near-zero and construct the Belief State yourself.** The split is already half-encoded in the setup's model routing (`../agent/COMPAT.md`: Архитектура=Opus, код=DeepSeek/GLM): heavy model + minimal prompt for the **Architect phase**, light/fast models for the **fixes** afterward — premium reasoning where the design is decided, premium speed where it's patched.

---

## When to leave the agent (this is not every task)

Same spirit as the GRACE-Full ≥2/4 gate — the clean room is for reasoning-hard architecture, not CRUD.

| Stay in the agent (`/planning-with-files` inline) | Move to a clean-room prompt (this guide) |
|---|---|
| CRUD / well-trodden stack, obvious layers | Novel domain, no reference architecture to pattern-match |
| ≤4 modules, low coupling | High coupling / cohesion trade-offs, ≥5 interdependent modules |
| Bugfix, small feature | Foundational decision that later tickets inherit (hard to reverse) |
| You already know the shape | You need the model's *latent* knowledge, not its default answer |

If ≥2 of the right-column conditions hold → run the Architect phase on a stripped prompt, then re-enter.

> Note: this ≥2/4 (architecture-hardness) is a DIFFERENT test from the GRACE-Full ≥2/4 (modules≥5 / multi-session / long-context / multi-agent) in PIPELINE Branch A. You can be architecture-hard without triggering GRACE-Full, and vice-versa. Evaluate them separately.

---

## Rule 1 — Heavy model, bare prompt, chat mode

Three levers, all pulled at once:

1. **Heavy model.** The setup already routes architecture to the strongest reasoner (Opus, or Gemini heavy in AI Studio). Light code models (DeepSeek V4, GLM 5.2, Grok Code Fast) are for implementation and fixes — the heavy tier earns its cost on design and requirements, not on churning out code.
2. **Bare system prompt.** Run it where *you* author every token of the system prompt — no vendor harness pre-seating the Belief State (see the surface table below).
3. **Chat, not agent.** No tool-use loop, no auto-editing. You are the orchestrator; the model reasons, you carry the artifact.

---

## Rule 2 — Where to find a low-residue surface (ranked)

Ranked by how little vendor prompt sits above your first token — least residue = most raw IQ available.

| Surface | System-prompt residue | Context in | Verdict for Architect phase |
|---|---|---|---|
| **Self-hosted** (vLLM / Ollama, open weights) | none — you set every token | manual | Purest. Use when weights are strong enough and you have the box. |
| **Provider API** (`system` param: Anthropic / DeepSeek / Gemini) | none but the model's base alignment; **you** author `system` | paste / files | Truest control at frontier quality. Your `../agent/PROMPT-FORMAT.md` template *becomes* the system prompt. |
| **Google AI Studio** | near-empty by design; now has GitHub integration + Code Execution | GitHub repo, files | Default for the Architect phase — free premium-tier reasoning. |
| **DeepSeek chat** | a line or two on safety, nothing more | paste | Fine when those few lines won't distort the domain. |
| ❌ **Agent harness** (Claude Code / Cursor / Copilot / OpenCode) | heavy — thousands of scaffolding tokens at top-of-context | native | **Not** for hard architecture. Great for execution, taxing for reasoning. |

> Note the tension with the setup's own `/judge` isolation and Collegium: the *judge* wants a clean **context** (no generator bias); the *architect* wants a clean **system prompt** (no harness bias). Different cleanliness, same principle — remove the wrong anchor from the highest-attention slot.

---

## Rule 3 — Inject the shamanism (your prompt IS the lever)

«Шаманство на промтах, гайдах, разметках кода» — not brute-forcing a pricier model. In the clean room `../agent/PROMPT-FORMAT.md` stops being buried inside someone else's `<guide>` and **becomes the system prompt itself** — top of context, highest attention, exactly where the levers bite:

- **L2/L4 — role + goal as the first tokens.** Open with role activation and `GOAL_ROOT`; the first sentence is the trajectory anchor (`../agent/PROMPT-FORMAT.md` L5).
- **L3 — GRACE / CAPS_SNAKE anchors.** `MODULE_CONTRACT`, `PBS_LEAF`, `SYNTHESIS_GATE` are rare tokens → Top-k attention beacons. Rare = high score.
- **L5 — superposition, forced.** Demand ≥3 architecture hypotheses, scored, before collapse. This is where the model's deep knowledge comes up — the second- and third-best trajectories the default answer would have skipped. Keep the decision lens *out* until `SYNTHESIS_GATE` (`../agent/PROMPT-FORMAT.md`).
- **Few-shot over micromanagement.** If you must steer syntax, show AI-generated snippets at the top of context — a model reads another model's examples better than it reads prose rules — and do **not** inject blunt corrections mid-reasoning; that freezes the Belief State.

Use the full template in `../agent/PROMPT-FORMAT.md §Template — Full`, promoted to the system slot.

---

## Rule 4 — GRACE makes it portable (the re-entry protocol)

The reason you *can* step out of the pipeline and come back with nothing lost: the deliverable is **GRACE-marked, model-agnostic** semantic markup. The clean-room session is not a detour — it produces the exact state files the pipeline already expects.

```
Clean-room Architect session (heavy model, your system prompt)
  │  reason under superposition → collapse at SYNTHESIS_GATE
  ▼
Emit the SAME artifacts the skills define:
  · task_plan.md  (architecture section: layers → modules → scenarios)
  · docs/development-plan.xml   (M-xxx modules, contracts, DF-xxx flows)   ← /grace-plan schema
  · docs/knowledge-graph.xml    (M-xxx + CrossLinks)                       ← /grace-plan schema
  · docs/adr/*.md               (decisions + rejected hypotheses)
  ▼
Re-enter PIPELINE.md — paste artifacts back as the state file the agent reads
  ▼
PHASE 2-PM gate (PM agent, isolated, ≠ architect model)  → GATE: APPROVE
  ▼
/judge plan  → GATE: PASS   → Visualize-before-tickets → /to-issues
```

In practice: run the Architect phase in AI Studio **with GRACE markup**, straight through AI Studio's GitHub integration, then light-model fixes downstream. GRACE is the passport — the markup travels between the clean room and the agent, so re-entry is a paste, not a re-derivation.

---

## Collegium still holds (it gets stronger)

The clean room does not bypass the Collegium — it sharpens it. The architect is now maximally *unconstrained*; the reviewers are still *isolated*:

- **Architect** — bare prompt, heavy model A (Opus / Gemini heavy).
- **PM review** (PHASE 2-PM) — different model, isolated context. Checks arch traces to `product_brief §7` user journey and ≥3 options were scored.
- **`/judge` plan** — Opus, fresh context, no architect history.

Never let the same session that designed the architecture also approve it — «без судьи коллегия плохо выбирает» (`../agent/COMPAT.md`).

---

## Anti-patterns

| ❌ | ✅ |
|---|---|
| Reason through hard architecture inside the agent harness because it's where you already are | Move it to a bare-prompt surface; the harness Belief State taxes reasoning |
| Brute-force a pricier model when the plan is weak | Work the prompt / guides / GRACE markup instead — a bigger model rarely fixes a weak plan |
| Micromanage syntax or make parallel edits mid-reasoning | Few-shot AI-generated snippets at top of context; never freeze the Belief State |
| Skip GRACE markup in the clean room ("it's just a chat") | No markup → no portable artifact → no clean re-entry. GRACE is the passport |
| Treat the clean-model decision as final — skip PM / judge gates | Gates don't move: PHASE 2-PM APPROVE + `/judge` PASS still required |
| Use a light/code model (Grok, GLM) for architecture | Heavy for design, light for fixes |
| Leak discovery-process terms into the clean-room prompt | Encapsulation still holds — this phase is post-brief; no discovery vocabulary crosses in |
| One plausible architecture, no alternatives | Superposition: ≥3 scored hypotheses before `SYNTHESIS_GATE` — that's where latent knowledge surfaces |
