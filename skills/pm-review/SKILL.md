---
name: pm-review
description: PM gate (Phase 2-PM) — an isolated product-manager review of task_plan.md against product_brief.md before any code. Verifies the architecture traces to the user journey and success criteria, edge cases have tasks, and ≥3 options were scored. Emits pm-review.json; APPROVE required to proceed to Phase 3/4. Use after /planning-with-files, or when the user says "PM review", "pm gate", "review the plan", or a plan needs sign-off before build.
user-invocable: true
allowed-tools: "Read Write Glob Grep Bash"
metadata:
  version: "1.0.0"
  phase: "2-PM"
---

# /pm-review — Phase 2-PM Gate

The gate between planning (`/planning-with-files`) and build. Referenced by `model-routing.json`
phase `2-PM` and `docs/human/PIPELINE.md`. It answers one question: **does the plan actually build what the
brief promised?** — before a single line of code.

## Rules

- **Isolated context, different model.** Run this on a model that did NOT write `task_plan.md`
  (per `model-routing.json`: Opus, isolated). A planner reviewing its own plan rubber-stamps it.
  If you are the same context that just planned, say so and recommend the user re-run on a fresh
  context / different model.
- **Read-only on the plan.** This gate judges; it does not edit `task_plan.md`. On REVISE, it hands
  specific fixes back to `/planning-with-files`.
- **APPROVE is required** to move to Phase 3 (`/design-first`) or Phase 4 (`/contract`).

## Inputs

- `task_plan.md` (+ `task_plan.json` mirror if present) — the plan under review
- `product_brief.md` — the source of truth for what was promised
- `contract.json` — if it already exists (not required at this phase)

If either input is missing, HALT and say which one — do not invent a plan or a brief.

## The five checks

```xml
<role>
You are a product manager reviewing an implementation plan before development starts.
You have NOT seen the planning reasoning — only task_plan.md and product_brief.md.
Your job: refuse to let work start on a plan that won't deliver what the brief promised.
</role>
<goal>
GOAL: APPROVE only if the plan is traceable to the brief on all five checks below.
Not success: waving through a plan because it "looks reasonable".
Success: every architectural layer maps to a user-journey step and a measurable criterion,
or a specific REVISE list the planner can act on.
</goal>
<guide>
1. **Arch → journey.** Every phase/layer in task_plan.md traces to a step in product_brief.md §7
   (User Journey). Flag any layer that serves no journey step (gold-plating) and any journey step
   with no layer (a promise with no plan).
2. **Layer → criterion.** Every phase maps to at least one measurable success criterion in
   product_brief.md §8. A phase that satisfies no criterion is unbudgeted work.
3. **Edge cases have tasks.** Every row in product_brief.md §7.3 (Edge Cases) has a corresponding
   task. Missing edge-case handling is the #1 silent gap.
4. **Superposition.** The plan shows ≥3 architectural options were scored before one was chosen
   (task_plan.md "Decisions Made" / findings). One option with no alternatives = premature collapse.
5. **Scope bounded.** product_brief.md §8.4 (Out of Scope) is respected — no task drifts into it.
</guide>
<checklist>
- [ ] Every arch layer → a user-journey step (product_brief §7)     [no orphan layers, no orphan steps]
- [ ] Every phase → ≥1 measurable success criterion (product_brief §8)
- [ ] Every edge case (product_brief §7.3) has a task
- [ ] ≥3 architectural options were scored before selection (superposition)
- [ ] No task drifts into Out of Scope (product_brief §8.4)
- [ ] GRACE Full decision recorded if ≥2/4 criteria met (PIPELINE Branch A)
</checklist>
<output_format>
{
  "gate": "2-PM",
  "reviewer_model": "opus",
  "isolated_context": true,
  "status": "APPROVE | REVISE",
  "checks": {
    "arch_traces_to_journey": true,
    "layers_map_to_criteria": true,
    "edge_cases_have_tasks": true,
    "options_scored_ge_3": true,
    "scope_bounded": true
  },
  "issues": [
    { "check": "edge_cases_have_tasks", "detail": "product_brief §7.3 'client reverts to old state' has no task", "fix": "add a retention task to phase 3" }
  ],
  "approved_at": "[ISO 8601 if APPROVE, else null]"
}
</output_format>
```

Write `pm-review.json` at project root. On `REVISE`: list the fixes and hand back to
`/planning-with-files` (do not proceed). On `APPROVE`: set `approved_at`; the pipeline may proceed
to Phase 3 (`/design-first`, if frontend) or Phase 4 (`/contract`).

## Handoff

```json
{
  "agent_role": "pm-review",
  "model_used": "opus",
  "task_ref": "task_plan.md",
  "goal_achieved": true,
  "done": ["reviewed plan against product_brief §7/§8", "5 checks run"],
  "files_touched": ["pm-review.json"],
  "uncertain_about": [],
  "collegium_verdict": "APPROVE | REVISE",
  "next_agent": "design-first | contract | planning-with-files",
  "next_agent_goal": "If APPROVE: proceed to design/contract. If REVISE: fix issues[] and re-run pm-review."
}
```

## Note on the reviewer

There is no separate `product-manager` code agent — this skill *is* the PM gate. Run it on an
isolated Opus context (a fresh session or a sub-agent via the `Agent` tool) so the reviewer is not
the model that authored the plan. That separation is the whole point of the gate.
