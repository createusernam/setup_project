# Structured Prompt Format

Standard for all agent prompts. Built on 6 LLM architecture layers — each layer is a lever.

## The 6-Layer Stack

```
L1: Physics          — token probabilities, attention mechanism
L2: Latent Space     — semantic trajectories in residual stream
L3: GRACE            — XML/CAPS anchors as Top-k attention beacons
L4: PCAM             — goal framing shapes what trajectory is entered
L5: Coconut / Belief — hold superposition; don't collapse prematurely
L6: State-First      — state files as Belief State anchors across turns
```

Each layer builds on the one below. Ignoring L4 (PCAM) means agent follows its own goal, not yours.
Ignoring L5 (superposition) means the model picks the first plausible answer, not the best one.

---

## L4: PCAM — Goal, Not Task

**PCAM = Purpose Centric Agent Methodology.** Six principles:

1. **Goal primacy** — agent receives WHY, not WHAT. WHY activates purpose-aligned trajectory.
2. **Guides not scripts** — recommendations map, not step-by-step script. Agent adapts to reality.
3. **Protocol rigidity at interfaces** — JSON schema + handoff.json are strict; internal steps are flexible.
4. **Plugin architecture** — each agent is replaceable; only interface contract is fixed.
5. **Self-healing** — agent detects when stuck; triggers PLAN-CONFIRM rather than hallucinating forward.
6. **Feedback loop** — handoff.json carries `uncertain_about` for next agent to address.

### Goal vs Task framing

| ❌ Task (script) | ✅ Goal (PCAM) |
|-----------------|---------------|
| "Step 1: read file. Step 2: extract functions. Step 3: write tests." | "Goal: ensure payment module behavior is predictable under edge cases. Guide: start with public API surface, prefer property-based tests for numeric logic." |
| "List all endpoints" | "Goal: document the API contract so a new developer can integrate without reading code." |
| "Refactor this function" | "Goal: make this function independently testable. Guide: dependency injection preferred over globals." |

### PBS — Purpose Breakdown Structure

Decompose from root goal to leaves. Each leaf ≤200 lines / ≤2000 tokens.

```
GOAL_ROOT: "Users can track their periods reliably offline"
  └─ GOAL_1: "Data persists without network"
       └─ TASK_1a: "Implement Dexie.js sync (≤200 lines, DeepSeek V4)"
       └─ TASK_1b: "Write sync tests (≤150 lines, GLM)"
  └─ GOAL_2: "Import from other apps works"
       └─ TASK_2a: "Parse CSV format (≤120 lines, DeepSeek V4)"
```

**Why ≤200 lines per task?** SFT training data is "torn book pages" — the model has seen each page but not the book. Large tasks cause strategic blindness past ~800 lines. Small tasks with goal alignment = the model connects pages via purpose, not position.

### PLAN-CONFIRM pattern

Before execution, agent builds its own plan from the goal and presents it for human confirmation.

```json
{
  "status": "needs_approval",
  "goal_understood": "...",
  "plan": [
    { "step": 1, "action": "...", "rationale": "...", "output": "..." }
  ],
  "assumptions": ["..."],
  "PLAN_CONFIRM": "Type APPROVE to proceed or describe changes"
}
```

After APPROVE → execute plan, write handoff.json.

---

## L5: Belief State + Superposition

### Belief State construction

The system prompt doesn't give instructions — it constructs the agent's Belief State (what the model believes to be true about its role, context, capabilities).

```
First sentence = role activation = trajectory anchor in residual stream
Context = situates the Belief State (what world the agent is in)
Goal = what the agent is trying to achieve in that world
Guide = how the agent approaches it (recommendations, not rules)
```

**Semantic freeze**: when a model keeps producing wrong outputs despite corrections, its Belief State is frozen. Fix: radical context switch — new conversation, different role framing, fresh state file.

### Superposition (Coconut-inspired)

Hold ≥3 hypotheses before collapsing. Each hypothesis is a different trajectory in latent space. Scoring forces explicit comparison before selection.

**Bad:** "The answer is REST because it's standard."
**Good:**
```json
"hypotheses": [
  { "id": "h1", "description": "REST API", "score": 0.72, "evidence": ["standard", "tooling"] },
  { "id": "h2", "description": "Resource-oriented RPC", "score": 0.65, "evidence": ["fewer endpoints", "type safety"] },
  { "id": "h3", "description": "Action-based API", "score": 0.41, "evidence": ["matches UI verbs"] }
],
"selected_hypothesis": "h1"
```

---

## L3: Vector Anchor Rules

Sparse attention selects Top-k tokens by score. **Rarer token = higher score = higher attention capture guarantee.**

Rules:
- Use `MODULE_CONTRACT`, `GOAL_ROOT`, `PHASE_CONFIRM`, `PBS_LEAF` — rare in training data
- Avoid "important", "note", "remember", "please" — common = low score
- XML-style tags (non-HTML) are high-signal: `<role>`, `<belief_state>`, `<goal>`, `<guide>`
- CAPS_SNAKE anchors in skill files mark phase boundaries: `PLAN_CONFIRM`, `PHASE_0`, `SYNTHESIS_GATE`
- Repeat anchors at start AND end of prompt (attention peaks at both ends)

---

## Template — Full

```xml
<role>
  <!-- BELIEF STATE ANCHOR: first sentence = trajectory -->
  You are [specific role, domain, years of experience].
  Your belief: [what the agent "knows" is true about this context].
</role>

<belief_state>
  <!-- Situates the agent in its world -->
  Project: [name, stack]
  Current state: [what exists, what decisions have been made]
  Artifacts: [list state files the agent should read first]
</belief_state>

<goal>
  <!-- PCAM: WHY, not WHAT -->
  GOAL_ROOT: [root goal — one sentence stating desired outcome]
  Success looks like: [observable outcome the agent can verify]
  Not success: [explicit anti-goal to avoid misalignment]
</goal>

<guide>
  <!-- PCAM: recommendations, not script -->
  Recommended approach: [first suggestion]
  If blocked: [self-healing trigger]
  Prefer: [architectural/style preference]
  Avoid: [known pitfall in this context]
</guide>

<plan_confirm>
  <!-- PCAM: agent builds own plan, presents for approval -->
  Before executing:
  1. Build your plan from the goal above
  2. Output status: "needs_approval" with your plan
  3. Wait for APPROVE before proceeding
  Marker: PLAN_CONFIRM
</plan_confirm>

<think_before_answering>
  <!-- SUPERPOSITION: enumerate before collapsing -->
  Step 1: List ≥3 distinct approaches to the goal
  Step 2: Score each on [relevant criteria 0.0–1.0]
  Step 3: Select highest-scoring
  Step 4: State what the rejected approaches explain better
  Marker: SYNTHESIS_GATE — do not collapse before this step
</think_before_answering>

<output_format>
  Return ONLY valid JSON:
  {
    "status": "success | error | needs_info | needs_approval",
    "goal_achieved": true,
    "data": { /* task-specific payload */ },
    "confidence": 0.0,
    "hypotheses": [
      { "id": "h1", "description": "...", "score": 0.0, "evidence": [] }
    ],
    "selected_hypothesis": "h1",
    "handoff": {
      "done": [],
      "files_touched": [],
      "uncertain_about": [],
      "test_status": "pass|fail|not_run",
      "next_agent": ""
    },
    "issues": [],
    "trace": [],
    "next_action": ""
  }
</output_format>

<critical_reminder>
  <!-- ATTENTION SPIKE: repeat most critical constraint at end -->
  [Repeat single most critical constraint]
  PLAN_CONFIRM before executing.
  SYNTHESIS_GATE before collapsing to one answer.
  Output valid JSON only. No prose before or after.
</critical_reminder>
```

---

## Metamodel Distortion Check

Before sending a goal/task to an agent, scan it for NLP distortions that hide missing requirements.

| Distortion | Pattern | Question to ask |
|------------|---------|-----------------|
| **Omission** (passive) | "the feature needs to be built" | Who builds? For whom? What exactly? |
| **Nominalization** | "the implementation", "user onboarding" | Implement what? Onboard how? What actions? |
| **Modal operator** | "must", "can't", "should" | Who says? What happens if we don't? |
| **Presupposition** | "since users need X" | Do they? What's the evidence? |
| **Omitted performative** | "this is important", "we can't" | To whom? Who decided? |
| **Cliché** | "best practices", "modern approach" | Which ones specifically? Why those? |

Run this check on:
- `value_proposition.md` before `/grill-with-docs`
- Research questions before `/researcher`
- User stories before `/contract`

---

## Short Form (simple tasks)

```
[ROLE: senior backend developer]
[GOAL: ensure payment module handles concurrent requests without race conditions]
[GUIDE: prefer optimistic locking, test with ≥3 concurrent writers]
[PLAN_CONFIRM: present approach before coding]
[OUTPUT: JSON { status, data, handoff }]
[ANCHOR: no locking implementation without tests]
```

---

## Anti-Patterns

| ❌ | ✅ |
|---|---|
| "Please help me with..." | "You are [role]. Goal: ..." |
| "Step 1: ... Step 2: ..." | Goal + Guide; agent plans own steps |
| "Return JSON with fields X, Y" | Provide actual JSON schema |
| One answer, no alternatives | ≥3 hypotheses → score → select |
| Critical constraint buried in middle | State at start (role) AND end (critical_reminder) |
| Generic words: "note", "important" | CAPS_SNAKE anchors, XML tags |
| Agent starts coding immediately | PLAN_CONFIRM gate before execution |
| Same model for coder + reviewer | Collegium of different models (see agents/team.md) |
