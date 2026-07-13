---
name: contract
description: Negotiate the "what done means" contract on disk before any autonomous code cycle starts. Produces contract.json with weighted criteria, user_flow (CJM-anchored), integrations (API contracts, data flow), restart threshold, and out-of-scope. Hard gate before /build-loop and /tdd. Use when starting a new feature, between /planning-with-files and the build cycle, or when user says "set up a contract", "what should done look like", "goal for this work", or invokes /contract. Triggers — contract, goal, "done means", acceptance criteria, rubric, user flow, integrations.
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep"
metadata:
  version: "1.1.0"
  authority: "Anthropic Applied AI talk, May 2026 — long-running-agents pattern"
---

# /contract — Contract-First Development

## Why this skill exists

From the Anthropic Applied AI talk on long-running agents (May 2026): the generator and the evaluator **must negotiate, on disk, what "done" means — before any code is written**. Self-evaluation is a trap; a standalone critic tuned against a concrete contract is tractable.

But "done means" cannot just be acceptance criteria. To run **autonomous** cycles without a human in the loop, the contract must also fix:

1. **User flow** — JTBD-framed primary path + error paths. The evaluator replays it via Playwright.
2. **Integrations** — API endpoints, request/response shapes, error codes, data flow across boundaries. Otherwise the generator hallucinates contracts on the fly.
3. **Acceptance criteria** — 15-30 granular, weighted, machine-verifiable rules.

Vague spec → vague critique → the generator shrugs. **27 granular criteria** (Anthropic's example) plus a fixed user flow and API spec → the agent knows exactly what fails and where.

## Where this fits in the pipeline

```
/grill-with-docs (with design lens if frontend) →  
  /planning-with-files →  
    [project setup: /design-rubric — ONE TIME if first frontend feature] →  
    [frontend: /design-first — wireframe → APPROVE → api-contract.json] →  
      /contract  ←  YOU ARE HERE
        → /to-issues  
          → /build-loop  OR  /tdd  
            → /code-review-expert  
              → ship
```

The contract is the **hard gate** before any autonomous cycle. `/build-loop` refuses to start if any required section is empty.

## Prerequisites

- `task_plan.md` from `/planning-with-files` — describes the scope and phases.
- `findings.md` if there's domain research worth referencing.
- For frontend features: **`design-contract.json` MUST exist at project root** (from one-time `/design-rubric`).
- For features touching APIs: existing OpenAPI spec or willingness to write one as part of this contract.

If `design-contract.json` is missing for a frontend feature, halt and tell the user to run `/design-rubric` first (it's a one-time per-project setup).

## Workflow

### 1. Classify the feature

Set three flags on the contract:

```json
{
  "is_frontend": true,
  "is_backend": true,
  "is_architecturally_complex": false
}
```

- `is_frontend` — touches UI. Triggers inheritance from `design-contract.json` and requires `user_flow`.
- `is_backend` — touches data or business logic. Requires `integrations.data_flow` and per-endpoint contract.
- `is_architecturally_complex` — `/grace-bridge` returned YES (≥2 of 4 criteria). If true, this contract references `development-plan.xml` and `verification-plan.xml` from `/grace-plan`.

Most features are both frontend AND backend. Backend-only (worker jobs, migrations, internal APIs) skip `user_flow` and design inheritance.

### 2. Fill user_flow (frontend features)

JTBD-framed primary path + error paths. This is what the evaluator will replay via Playwright. Each step is a Playwright-executable action.

```json
"user_flow": {
  "linked_cjm": "docs/cjm/goal-creation.md",
  "jtbd": "Накопить на путешествие к конкретной дате",
  "primary_path": [
    { "step": 1, "action": "navigate to /goals", "expect": ".goals-list visible" },
    { "step": 2, "action": "click 'Накопить на путешествие'", "expect": "form modal opens" },
    { "step": 3, "action": "type '120000' in amount, '2026-12-31' in deadline", "expect": "submit button enabled" },
    { "step": 4, "action": "click submit", "expect": "toast 'Цель сохранена' within 2s" },
    { "step": 5, "action": "wait for redirect", "expect": "/dashboard shows new goal card" }
  ],
  "error_paths": [
    { "condition": "amount < 0", "expect": "inline error 'Сумма должна быть положительной', submit disabled" },
    { "condition": "deadline in past", "expect": "inline error 'Дата должна быть в будущем'" },
    { "condition": "POST /api/goals returns 500", "expect": "retry button visible, offline-style banner" }
  ]
}
```

If `linked_cjm` points to a file that doesn't exist yet, write the CJM inline as `primary_path` + `error_paths` here (`/grill-with-docs` does not guarantee a `docs/cjm/` file — `CONTEXT.md`/`domain.md` are its outputs).

### 3. Fill integrations (any feature touching cross-boundary state)

This is the section that prevents the generator from hallucinating API contracts mid-cycle.

```json
"integrations": {
  "data_flow": "GoalCreateForm (react-hook-form) → POST /api/goals → goals table (PG) → invalidate ['goals'] query → /dashboard re-renders new goal card",
  "frontend_calls": [
    {
      "from": "src/components/GoalCreateForm.tsx",
      "method": "POST",
      "endpoint": "/api/goals",
      "request_schema": {
        "title": "string, 1..200",
        "amount": "number > 0",
        "deadline": "ISO date in future"
      },
      "response_201": { "id": "uuid", "createdAt": "ISO date" },
      "response_400": { "error": "string", "field": "string" },
      "response_500": "retry-with-backoff handled by react-query"
    }
  ],
  "backend_endpoints": [
    {
      "path": "POST /api/goals",
      "handler": "api/routes/goals.ts:createGoal",
      "validates": "zod schema: title 1..200, amount > 0, deadline > now()",
      "writes": "INSERT INTO goals (id, user_id, title, amount, deadline)",
      "side_effects": "none",
      "auth": "session required"
    }
  ],
  "schema_changes": [
    { "table": "goals", "change": "no schema change required (existing columns sufficient)" }
  ],
  "external_services": []
}
```

For pure backend features, `frontend_calls` is empty and the user_flow is replaced by `cli_flow` or `job_flow` describing how the change is exercised.

If an OpenAPI spec already exists, reference it: `"openapi_spec": "api/openapi.yaml#/paths/~1api~1goals/post"`.

### 4. Fill criteria

15-30 weighted, machine-checkable criteria. Inherit design criteria from `design-contract.json` by reference (don't re-derive):

```json
"inherits": ["design-contract.json"],
"criteria": [
  {
    "id": "c1-flow-happy-path",
    "category": "functionality",
    "weight": 5,
    "must_pass": true,
    "check": "primary_path completes end-to-end without manual intervention",
    "verify": { "method": "playwright", "steps": "replay user_flow.primary_path" }
  },
  {
    "id": "c2-flow-amount-negative",
    "category": "functionality",
    "weight": 3,
    "must_pass": true,
    "check": "amount=-1 produces inline error and disables submit",
    "verify": { "method": "playwright", "steps": "fill amount=-1; expect .field-error visible; expect button[type=submit] disabled" }
  },
  {
    "id": "c3-api-contract-201",
    "category": "functionality",
    "weight": 4,
    "must_pass": true,
    "check": "POST /api/goals with valid body returns 201 with {id, createdAt}",
    "verify": { "method": "test", "command": "npm test -- api/routes/goals.spec.ts -g 'POST /api/goals success'" }
  },
  {
    "id": "c4-api-contract-400",
    "category": "functionality",
    "weight": 3,
    "must_pass": false,
    "check": "POST /api/goals with deadline in past returns 400 with field='deadline'",
    "verify": { "method": "test", "command": "npm test -- -g 'POST /api/goals invalid deadline'" }
  },
  {
    "id": "c5-craft-zod-validation",
    "category": "craft",
    "weight": 2,
    "must_pass": false,
    "check": "request validation uses shared zod schema, not ad-hoc if-checks",
    "verify": { "method": "grep", "command": "grep -E 'z\\.object|GoalCreateSchema' api/routes/goals.ts" }
  }
]
```

Categories and weighting (defaults; override per project):

| Category | When | Default weight |
|----------|------|----------------|
| `functionality` | Always — covers user_flow + integrations | 3-5 |
| `design` | Frontend (inherited from design-contract) | 2-3 |
| `craft` | Code quality, test coverage, type safety | 2 |
| `security` | Auth, payments, untrusted input | 5 (must_pass) |
| `perf` | User-facing latency budgets | 1-3 |
| `accessibility` | Public UI | 2 |
| `i18n` | RU UI (Trium/Lumiorama/Lua) | 1 |

Per Anthropic Opus 4.6+ note: weight design+originality higher than functionality (model already nails functionality).

### 5. Write contract.json and lock

Save to project root. Compute sha256 attestation:

```bash
sha256sum contract.json | awk '{print $1}' > .contract-attestation
```

Both `/build-loop` and `/code-review-expert` verify this hash before grading. Mismatch = `[CONTRACT TAMPERED]` halt.

### 6. Hand off

Print:

```
contract.json written — 23 criteria, locked to sha256:abc123…
  user_flow:    5 primary steps + 3 error paths
  integrations: 1 frontend call, 1 backend endpoint, 0 schema changes
  criteria:     functionality×8, design×9 (inherited), craft×4, security×2
  
Hard gate: /build-loop will refuse to start if any of these sections are stripped.
Next: /to-issues  (derives issues per criterion-slice or user_flow step)
   → then /build-loop  (autonomous cycle)
```

## Verify methods

| Method | Use for | Field |
|--------|---------|-------|
| `grep` | Code-level invariants | `command` — exit 0 = pass |
| `test` | Unit/integration tests | `command` — runner with -g pattern |
| `typecheck` | TS constraints | `command` — `tsc --noEmit` etc. |
| `playwright` | User flow replay, UI state, screenshots | `steps` — Playwright sequence (executed by evaluator) |
| `lighthouse` | Performance, a11y | `min_score` per category |
| `api_contract` | Schema validation against OpenAPI | `command` — `npx dredd` or similar |
| `trace` | Execution trajectory: did the run walk the intended path? | `command`, `flow`, `expect_sequence`, `forbid` |
| `manual` | Subjective taste (rare — push to verifiable where possible) | `prompt` |

**Avoid `manual` for >30% of criteria.** Push to playwright/grep/test.

### `trace` — grading the trajectory, not just the endpoint

An assertion says the output equalled X. A trace says the system *got there the intended way*. The
difference matters because an LLM optimises against whatever it is graded on: given only equality
assertions, it will produce code that satisfies them and fails in the cases nobody asserted. Grading
the trajectory is much harder to game — the run has to actually walk the path.

This is the contract-side half of the GRACE Lite log anchors (`[Module][function][BLOCK_NAME]`,
PIPELINE §GRACE Lite rule 4) and the `<CriticalFlows>` in `verification-plan.xml`. Anchors that
nothing grades against are decoration; this is what reads them.

```json
{
  "id": "c9-trace-goal-creation",
  "category": "behavior",
  "weight": 4,
  "must_pass": true,
  "check": "creating a goal walks validate → persist → emit, and never enters the error branch",
  "verify": {
    "method": "trace",
    "command": "npm run test:e2e -- --grep 'create goal' 2>&1 | tee .build-loop/run.log",
    "flow": "goal-creation",
    "expect_sequence": [
      "[Goals][createGoal][VALIDATE_INPUT]",
      "[Goals][createGoal][PERSIST]",
      "[Events][emit][GOAL_CREATED]"
    ],
    "forbid": ["[Goals][createGoal][ERROR]", "[DB][query][RETRY]"]
  }
}
```

Grading (done by the evaluator, see `/build-loop` §2b):

1. Run `command`, capture stdout+stderr.
2. `expect_sequence` — the anchors must appear **in this order** (other lines may sit between them).
   A missing or out-of-order anchor scores 0.
3. `forbid` — any match scores 0, regardless of the sequence.
4. **Semantic verdict on the whole trace.** Beyond the mechanical checks, the evaluator reads the
   captured log and states whether the trajectory is coherent for `flow` — retries that "succeeded",
   fallbacks that silently swallowed a failure, a path that passed by accident. A binary PASS/FAIL is
   a weak signal; the critique carries the reasoning.

`flow` names the corresponding `<Flow>` in `verification-plan.xml` when GRACE Full is on. Without
GRACE Full, `flow` is a free-text label and the anchors are still required.

**When to use it:** business logic whose correctness is a *path*, not a value — ETL steps, payment
state machines, sync/merge, retry and fallback behavior. These are exactly the cases where equality
assertions look green and the feature is broken.

## Hard gate logic

`/build-loop` validates contract.json on startup:

```
✗ HALT if: user_flow.primary_path is empty AND is_frontend === true
✗ HALT if: integrations.data_flow is empty AND (is_frontend || is_backend)
✗ HALT if: criteria.length < 10
✗ HALT if: must_pass criteria with verify.method === "manual" exist (humans gate must_pass, not manual prompts during autonomous run)
✗ HALT if: .contract-attestation sha doesn't match contract.json
✓ PROCEED otherwise
```

This is the load-bearing rule: **no integration spec + no user flow → no autonomous cycle**. Force the gate.

## Composition with other skills

- **`/planning-with-files`** writes `task_plan.md` (phases). `/contract` writes `contract.json` (acceptance + integration + flow). Both at project root, both attested.
- **`/design-rubric`** writes `design-contract.json` at project root ONCE per project. `/contract` references it via `inherits`. Don't duplicate design criteria here.
- **`/to-issues`** reads contract.json. Each issue gets a slice of user_flow steps + relevant criteria. The autonomous cycle picks up an issue and inherits the contract context.
- **`/build-loop`** is the primary consumer — hard-gated on contract.json being complete.
- **`/code-review-expert`** (modified v2.0+) — reads contract.json if present; grades against it before falling back to generic checklist.
- **`/grace-plan`** — produces `verification-plan.xml`. Its `<CriticalFlows>` and log markers are what `verify.method: trace` criteria grade against (see §Verify methods). If GRACE Full ran, every flow marked `must_remain_observable` should have a `trace` criterion here — otherwise the observability requirement is unenforced.
- **`/scaffold`** — writes the module skeletons with the GRACE Lite anchors (`START_BLOCK_*`, `[Module][function][BLOCK]` logs) that `trace` criteria reference. Write the contract first: the scaffold is generated *from* it.

## Portable invocation (OpenCode, DeepSeek, etc.)

The contract.json **artifact** is portable. Any model on any CLI that can read JSON can grade against it. What's NOT portable:

| Component | Claude Code | OpenCode | DeepSeek-as-model | Fallback |
|-----------|-------------|----------|-------------------|----------|
| `Skill` invocation `/contract` | native | needs `AGENTS.md` reference | needs prompt manually | paste the SKILL.md body into the chat |
| `Agent` tool (sub-agents) | native | `task` tool similar | not native | sequential turns in single session with explicit `[ROLE: generator]` / `[ROLE: evaluator]` framing and `/clear` between roles |
| Playwright MCP | `claude mcp add playwright -- npx -y @playwright/mcp@latest` | `~/.config/opencode/mcp.json` block (see below) | inherits from host CLI | identical MCP server, stdio transport |
| `contract.json` | read with Read tool | identical | identical | portable, language-agnostic |
| `.contract-attestation` | sha256 check | identical | identical | portable |

OpenCode MCP config (`~/.config/opencode/opencode.json` or project `.opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "@playwright/mcp@latest", "--headless"],
      "enabled": true
    }
  }
}
```

For DeepSeek-Coder used as model backend inside Claude Code or OpenCode: nothing changes — the CLI handles tools and Playwright MCP, the model just produces text.

For DeepSeek invoked standalone (no CLI): use contract.json as system prompt, run Playwright manually via `npx playwright test` against a generated spec file. Lose the generator/evaluator separation; humans take that role.

## Anti-patterns

| Don't | Do instead |
|-------|-----------|
| Skip `user_flow` "because it's obvious" | Encode it — Playwright will replay these exact steps |
| Skip `integrations` because the endpoint feels small | Even one POST deserves request/response shape lock |
| Re-derive design criteria from prose | Inherit `design-contract.json` by reference |
| Write `must_pass: true` on >30% of criteria | Reserve for genuinely load-bearing (security, data integrity) |
| Modify contract.json mid-loop without re-attesting | Re-run `/contract` to renegotiate; document the change |
| `manual` verify method for must_pass criteria | Humans gate must_pass before autonomous runs; manual ≠ autonomous |
| Use this for bugfixes | Bugfix scope is the issue + regression test; `/diagnose` + `/tdd` is the path |
| <10 criteria | Push for granularity — at 5 criteria, evaluator critique is useless |

## Files

- `templates/contract.json` — v2 schema starting template. Set `is_frontend` / `is_backend` in §1 (Classify the feature) for frontend / backend / fullstack shapes — the flags drive which sections (`user_flow`, `integrations`, design inheritance) are required, so there are no separate per-shape example files.
