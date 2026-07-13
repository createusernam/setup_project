---
name: scaffold
description: Generate GRACE-marked module skeletons from the plan and contract, so the cheap implementer model gets a code few-shot instead of a spec. Writes MODULE_CONTRACT, FUNCTION_CONTRACT, typed signatures, START_BLOCK anchors, block-anchored logs and IMPL directives; leaves block bodies unimplemented. Runs on the strong model (Opus) between /to-issues and the build cycle. Use when starting Phase 6 on a greenfield feature, or when user says "scaffold", "write the skeleton", "prototype the modules", "prepare for the implementer". Not for bugfixes.
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep Agent TaskCreate TaskUpdate TaskList"
metadata:
  version: "1.0.0"
  phase: "5.5"
  authority: "GRACE — code-as-few-shot over spec-as-handoff; contracts as semantic shield"
---

# /scaffold — the handoff to the implementer is code, not a spec

## Why this skill exists

The obvious way to drive a cheap implementer model is: strong model writes a spec, cheap model reads
the spec and writes the code. It is also the wrong way, for two measured reasons:

1. **A spec costs about what the code costs.** A verbose strong model spends roughly 80% of the
   target code's token count writing the spec for it. You paid Opus prices to *describe* the work, and
   you still have to pay to have it done.
2. **A spec is a weak prior; code is a strong one.** In-context learning is imitation. Give a model a
   prose spec and it composes from general priors. Give it a half-written module — real imports, real
   types, contracts, log anchors, named blocks — and it is a few-shot example: the model continues *in
   the same style*, inside boundaries it can see. Base training (FIM) taught these models to lean on
   code, not on documentation. Contracts embedded in the code are the one form of intent they cannot
   route around.

So the strong model writes the **skeleton**: every boundary, signature, contract, block and log
anchor — and no business logic. The cheap model fills the block bodies. Most of the token spend, and
all of the routine work, moves down-tier. The GRACE Lite markup gets written by the model that is
actually good at it, rather than being demanded from the weakest link in the chain.

## Where this fits

```
/contract → /judge → VIZ gate → /to-issues → /scaffold → /build-loop | /tdd → /judge feature → ship
                                              ▲
                                              you are here — last step on the strong model
```

**Not for bugfixes.** A bugfix has existing code; the skeleton already exists. Use `/diagnose` → `/tdd`.

## Prerequisites — HARD GATE

```
1. contract.json exists and .contract-attestation matches its sha256
2. task_plan.md exists (PBS leaves — each ≤200 lines)
3. If GRACE Full is on: docs/development-plan.xml and docs/knowledge-graph.xml exist
   (module IDs, types, depends, verification-refs — the skeleton is generated FROM them)
4. If contract.json.is_frontend: design-contract.json exists and is attested
5. Git working tree is clean — the scaffold lands as one reviewable commit
6. You are running on the routed model for this phase:
   bash ~/.claude/scripts/model-check.sh 5.5     # → opus
```

Halt with a precise diagnostic if any check fails. A scaffold generated from an unattested contract
is a scaffold of the wrong thing, propagated into every module the implementer touches.

## What a skeleton contains — and what it must not

| Include | Exclude |
|---------|---------|
| `// FILE:` + MODULE_CONTRACT (PURPOSE / SCOPE / DEPENDS) | Business logic of any kind |
| Real imports, real types, full interface definitions | Speculative helpers "the implementer might want" |
| Exported signatures with FUNCTION_CONTRACT (PURPOSE / INPUTS / OUTPUTS / SIDE_EFFECTS) | Implementations that "were easier to just write" |
| `START_BLOCK_*` / `END_BLOCK_*` around each logical step | Blocks with no name, or names that aren't in the plan |
| A block-anchored log line per block: `[Module][function][BLOCK]` | Silent blocks — a `trace` criterion has nothing to grade |
| `IMPL:` directive in every empty block — the micro-spec, in place | Bare `TODO` with no instruction |
| `throw new Error("NOT_IMPLEMENTED: <block>")` at each unimplemented exit | Fake return values that let a broken path look green |
| `RATIONALE:` at each non-obvious decision | Restating what the code plainly says |
| Mocks for external calls, typed to the real contract | Mocks that don't match `integrations.backend_endpoints` |

**The skeleton must typecheck and must not run.** If it doesn't typecheck, the cheap model spends its
budget fixing types instead of writing logic. If it runs — if you left plausible return values in —
then a half-built feature looks green in the evaluator, and the loop optimises against a lie.

## Reference skeleton

```ts
// FILE: src/goals/create.ts
// START_MODULE_CONTRACT
//   PURPOSE: Create a savings goal for the current user and emit the domain event
//   SCOPE: validation, persistence, event emission. NOT: goal editing, deletion, listing
//   DEPENDS: M-DB, M-EVENTS, M-AUTH
//   LINKS: docs/knowledge-graph.xml#M-GOALS
// END_MODULE_CONTRACT

import { db } from "../db";                 // M-DB
import { emit } from "../events";           // M-EVENTS
import type { Session } from "../auth";     // M-AUTH

export interface GoalDraft {
  title: string;
  targetAmount: number;   // minor units — never floats (RATIONALE: currency rounding)
  deadline: string;       // ISO-8601 date
}

export interface Goal extends GoalDraft {
  id: string;
  createdAt: string;
}

// START_CONTRACT: createGoal
//   PURPOSE: Validate a goal draft, persist it, emit GOAL_CREATED
//   INPUTS: { session: Session, draft: GoalDraft }
//   OUTPUTS: { Goal }
//   SIDE_EFFECTS: db write (goals); event GOAL_CREATED
//   ERRORS: ValidationError (400) on invalid draft; never throws on a valid one
// END_CONTRACT: createGoal
export async function createGoal(session: Session, draft: GoalDraft): Promise<Goal> {
  // START_BLOCK_VALIDATE_INPUT
  logger.info("[Goals][createGoal][VALIDATE_INPUT] validating draft", { correlationId: session.id });
  // IMPL: reject targetAmount <= 0 and deadline in the past with ValidationError.
  //       Contract criterion c4-api-contract-400 expects HTTP 400, not 500, for both.
  throw new Error("NOT_IMPLEMENTED: VALIDATE_INPUT");
  // END_BLOCK_VALIDATE_INPUT

  // START_BLOCK_PERSIST
  // RATIONALE: single insert, no transaction — the event is emitted after commit, so a failed
  //            emit must not roll back a goal the user already saw succeed.
  logger.info("[Goals][createGoal][PERSIST] inserting goal", { correlationId: session.id });
  // IMPL: insert into goals (see docs/development-plan.xml#M-GOALS interface); return the row.
  throw new Error("NOT_IMPLEMENTED: PERSIST");
  // END_BLOCK_PERSIST

  // START_BLOCK_EMIT_EVENT
  logger.info("[Events][emit][GOAL_CREATED] emitting", { correlationId: session.id });
  // IMPL: emit("GOAL_CREATED", { goalId }). Failure here is logged, never thrown (see RATIONALE above).
  throw new Error("NOT_IMPLEMENTED: EMIT_EVENT");
  // END_BLOCK_EMIT_EVENT
}
```

Note what this hands the implementer: the error contract (400 not 500), the money-as-integer decision,
the commit-then-emit ordering and *why*, the exact block names a `trace` criterion will grade, and the
log anchor format. None of that survives a prose spec intact — and all of it is what a cheap model
would otherwise invent differently in every module.

## Workflow

### 1. Read the sources of truth

- `contract.json` — criteria, `user_flow`, `integrations` (endpoint shapes, data flow)
- `docs/development-plan.xml` — module list, contracts, interfaces, build order (waves)
- `docs/knowledge-graph.xml` — module IDs, types, depends, verification-refs
- `docs/verification-plan.xml` — `<CriticalFlows>` and log markers: **block names must match these**
- `task_plan.md` — PBS leaves; one leaf ≈ one skeleton file
- `design-contract.json` — for frontend: token names, component boundaries

If GRACE Full did not run, derive modules from `task_plan.md` + `contract.json.integrations` and say so
in the summary — the skeleton is weaker without the graph, and the human should know.

### 2. PLAN_CONFIRM

Present, before writing a single file:

- The file list (path → module ID → PBS leaf → target size)
- For each file: block names, and which `trace`/`test` criteria they serve
- What you will mock, and against which contract
- Anything in the plan you cannot scaffold without guessing — **ask, don't invent**. A guess here is
  copied by the implementer into every module.

Wait for APPROVE.

### 3. Generate

One file per module, in `development-plan.xml` wave order (dependencies first — a skeleton that
imports a module that doesn't exist yet won't typecheck).

Rules while writing:
- Block names come from the plan and the verification flows. Do not invent new ones — a `trace`
  criterion that names `PERSIST` and code that logs `SAVE` is a criterion that can never pass.
- Every `IMPL:` states the *what* and the *constraint*, never the *how*. The implementer picks the how;
  that is the work you are paying the cheap model for.
- Cross-module calls use the real signature of the other skeleton, not a mock — the graph must be
  walkable.
- External I/O gets a typed mock matching `integrations`, with an `IMPL:` to swap it for the real call.

### 4. Verify the scaffold before handing it over

```bash
bash ~/.claude/scripts/grace-lint.sh --profile autonomous src/   # every anchor present
npm run typecheck                                                # must pass — implementer must not fix types
grep -rn "NOT_IMPLEMENTED" src/ | wc -l                          # = number of blocks awaiting logic
grep -rln "NOT_IMPLEMENTED" src/ | xargs grep -Ln "IMPL:"        # must be empty: no block without a directive
```

All four must be clean. A scaffold that fails its own lint teaches the implementer to skip the markup —
it is a few-shot example, and it will be imitated in both directions.

### 5. Commit and hand off

Commit the scaffold on its own (`scaffold: <feature> — N modules, M blocks awaiting implementation`),
so the implementer's diff is *only* logic and the review can tell them apart.

Write `handoff.json` (COMPAT schema): `agent_role: "architect"`, `model_used`, `files_touched`,
`done` (modules scaffolded), `uncertain_about` (anything you had to assume), `next_agent:
"implementer"`, `next_agent_goal: "fill NOT_IMPLEMENTED blocks; do not alter contracts, block names,
or log anchors"`.

## The implementer's rules (state these in the Phase 6 prompt)

The scaffold only pays off if the cheap model respects it:

1. **Fill block bodies. Do not restructure.** Contracts, block names and log anchors are fixed — they
   are what the evaluator grades against.
2. **Delete `NOT_IMPLEMENTED` throws as you implement them.** A leftover throw is an unfinished block,
   and the loop treats it as such.
3. **Keep the log lines.** They are the trace the evaluator reads.
4. **If an `IMPL:` directive is wrong or impossible, stop and say so** — do not "fix" it by changing the
   contract. That is a `PLAN_CONFIRM` back to the architect.
5. New file? It needs a MODULE_CONTRACT, same as the scaffolded ones.

## Anti-patterns

| Don't | Do instead |
|-------|-----------|
| Write a spec doc for the implementer | Write the skeleton — it *is* the spec, in the form the model imitates |
| Implement "the easy parts" while scaffolding | Leave every block empty; you're paying Opus rates for boundaries, not for loops |
| Leave plausible stub returns (`return []`) | `throw new Error("NOT_IMPLEMENTED: …")` — a half-built path must fail loudly, not look green |
| Bare `TODO` | `IMPL:` with the constraint and the criterion it serves |
| Invent block names | Take them from `verification-plan.xml` / the trace criteria |
| Scaffold every module up front for a 20-module feature | Scaffold one wave at a time; the plan changes as waves land |
| Skip `/scaffold` "because the contract is detailed enough" | The detail is the point — it belongs in the code, where the model cannot ignore it |

## Portable invocation

The artifact is plain source files — portable everywhere. What differs is only who writes them:
run `/scaffold` on the strong model (Claude Code with Opus; OpenCode with an Opus/Sonnet route), then
switch the model to the implementer tier for Phase 6. In a single-model setup the skill still helps —
the skeleton pass and the logic pass are different tasks, and separating them keeps the contracts
intact — but the cost argument disappears, so the gain is quality only.
