---
name: risk-review
description: Independently review T4 security, privacy, safety, regulatory, migration, operational, and irreversible delivery risks before contract authoring. Use when the selected setup pipeline tier is T4, when Phase 3r is requested, or when a consequential change needs a structured PASS, REVISE, or STOP risk verdict plus staged rollout and rollback evidence.
---

# Risk Review

Produce the T4 decision artifact that Phase 4 consumes. Work in a context isolated from the plan
author when possible. Do not write the delivery contract or implementation in this phase.

## Inputs

Read the attested project artifacts that exist:

- `product_brief.md` and `evidence-handoff.json`;
- `task_plan.md`, `pm-review.json`, `CONTEXT.md`, and relevant ADRs;
- `docs/development-plan.xml`, `docs/verification-plan.xml`, and
  `docs/knowledge-graph.xml`;
- approved design/API artifacts when frontend behavior exists;
- current system/code evidence for migrations, security boundaries, rollback, and operations.

Stop if the approved plan or architecture artifacts are missing. A risk review cannot repair an
unapproved plan silently.

## Workflow

1. Copy the project templates `risk-review.json` and `rollout-plan.json`; their adjacent schemas are
   authoritative for fields and allowed values.
2. Identify concrete failure scenarios. Allowed categories are `security`, `privacy`, `safety`,
   `regulatory`, `data_migration`, `operational`, `irreversibility`, and `other`.
3. For each scenario, record impact (`low|medium|high|critical`), likelihood
   (`low|medium|high`), mitigation, verification reference, owner, residual risk
   (`low|medium|high`), and status (`open|mitigated|accepted`).
4. Define staged rollout stages and a usable rollback trigger, action, and owner in
   `rollout-plan.json`. `rollback.defined` becomes `true` only when those fields are executable;
   set plan `status` to `ready` only when at least one stage and the rollback are usable.
5. Ask the accountable human only for residual-risk acceptance or a missing policy decision. Record
   that identity in `accepted_by`; do not infer consent from chat fluency or a model verdict.
6. Set one verdict:

   - `PASS`: every high/critical scenario is mitigated or explicitly accepted, verification is
     traceable, rollback is defined, staged rollout is concrete, and no blocking question remains;
   - `REVISE`: the change may proceed after named mitigation, evidence, ownership, or rollout gaps
     are fixed;
   - `STOP`: risk cannot be reduced or responsibly accepted within the approved scope.

## Output and handoff

Write exactly:

- `risk-review.json` — current stable Phase 3r verdict;
- `rollout-plan.json` — staged rollout and rollback plan.

Do not substitute a timestamped report for these stable paths. After human review, the operator
validates the adjacent schemas, attests both files, and runs `setup-preflight 4 .`. A `REVISE` or
`STOP` verdict never enters contract authoring.
