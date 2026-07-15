# Architecture Handoff Guide

This document defines what architecture work must receive and return so it can move through the
setup pipeline. It does not prescribe an architecture method, prompting technique, model, tool, or
diagramming notation. Use the approach that fits your project and team.

The architecture handoff sits between planning and the PM/contract gates. Its purpose is to make
decisions explicit, traceable, and usable by the next person or agent without replaying the design
conversation.

## Required inputs

Use the artifacts that exist for the selected risk tier. Do not invent missing facts.

| Input | What architecture may rely on |
|---|---|
| `product_brief.md` | outcome, users, scope, journeys, success criteria, constraints |
| `evidence-handoff.json` | evidence status, assumptions, open questions, decision and validation stage |
| `CONTEXT.md` | project vocabulary, domain rules, current system context |
| `docs/adr/` | decisions already made and constraints that must not be reopened silently |
| current code and interfaces | existing module boundaries, APIs, data stores, operational behavior |
| `task_plan.md` | work decomposition and the scope of the current change |

If an input conflicts with another input, record the conflict and return it to the artifact owner.
Architecture must not silently promote an assumption to a requirement or expand the approved scope.

## Decisions the handoff must make explicit

Record only decisions relevant to the change. A small reversible change may need a few lines; a
cross-module or high-risk change needs more detail.

1. **System boundary** — what is inside this change and what remains external.
2. **Responsibilities** — which component owns each behavior or state transition.
3. **Interfaces and data flow** — inputs, outputs, persistence, errors and external dependencies.
4. **Quality constraints** — security, privacy, reliability, performance, accessibility and
   operability requirements that affect the design.
5. **Failure and recovery** — where the flow can fail, how failure is observed, and how the system
   recovers or rolls back.
6. **Verification** — how each significant responsibility and interface will be tested or observed.
7. **Decision rationale** — why consequential choices were made, including material trade-offs and
   alternatives when they affect future work.

The user remains responsible for choosing the architecture method and final design. Pipeline gates
check the completeness and traceability of the result, not whether a particular design school or
tool was used.

## Minimum output by risk tier

| Tier | Minimum architecture handoff |
|---|---|
| T0 | changed files/components, targeted verification, rollback if relevant |
| T1 | affected behavior, root-cause boundary, regression coverage |
| T2 | component responsibilities, interfaces/data flow, risks, verification links |
| T3 | T2 plus module/dependency view, decision records, GRACE Full artifacts and PM review |
| T4 | T3 plus risk/threat review, staged rollout, rollback and audit evidence |

The canonical tier routes and required artifacts live in `../../pipeline-machine.json`.

## Portable handoff formats

### `task_plan.md` architecture section

The exact prose structure is flexible, but each significant component should be representable with
the following fields:

```yaml
id: M-001
name: account-service
purpose: Own account creation and account state transitions
responsibilities:
  - validate account creation requests
  - persist account state
depends_on:
  - identity-provider
interfaces:
  - POST /accounts
data_owned:
  - accounts
journey_refs:
  - product_brief.md#7-user-journey
criterion_refs:
  - c1-account-created
verification_refs:
  - tests/account_creation_test.py
risks:
  - duplicate requests
```

Use project-native names and omit fields that genuinely do not apply. Do not copy this example's
domain terms into a project.

### Architecture decision record

Create an ADR for a consequential or hard-to-reverse decision:

```markdown
# ADR NNN: Decision title

## Context
Facts, constraints, and the decision that must be made.

## Decision
The selected approach and its boundary.

## Consequences
Benefits, costs, risks, operational effects, and follow-up work.

## Alternatives considered
Material alternatives and why they were not selected. Omit when no meaningful choice existed.

## Evidence and assumptions
Links to supporting artifacts; assumptions and open questions remain labelled.
```

### GRACE Full artifacts

For routes that require GRACE Full, use the schemas and vocabulary owned by the GRACE skills:

- `docs/development-plan.xml` — modules, responsibilities, dependencies, interfaces and flows;
- `docs/verification-plan.xml` — verification references and critical flows;
- `docs/knowledge-graph.xml` — stable identifiers and cross-links between artifacts;
- `docs/adr/*.md` — consequential decisions and trade-offs.

Run `/grace-plan` to create or validate these formats. GRACE markup is a transfer format here; it
does not determine which architecture the user must choose.

## Quality checklist

Before handing the result to `/pm-review`, confirm:

- [ ] Every planned component serves at least one journey step or success criterion.
- [ ] Every in-scope journey step and edge case has an implementation responsibility.
- [ ] System boundaries, external dependencies, interfaces and owned data are explicit.
- [ ] Assumptions and unresolved questions are labelled and retain their evidence status.
- [ ] Significant failure paths have detection, recovery, and verification.
- [ ] Consequential decisions have a rationale and material trade-offs recorded.
- [ ] The design stays within the brief's scope and respects existing ADRs.
- [ ] Required tier-specific artifacts are present and syntactically valid.

This checklist checks the handoff, not the private reasoning process that produced it.

## Re-entry into the pipeline

1. Save the architecture section in `task_plan.md` and any required ADR/GRACE artifacts.
2. Attest or register changed artifacts in `.pipeline-state.json` where the route requires it.
3. Run `/pm-review`; it checks plan-to-brief traceability, coverage, risk, and scope.
4. On `APPROVE`, continue to design/contract gates selected by `pipeline-machine.json`.
5. On `REVISE`, return specific gaps to the artifact owner. Do not repair missing product evidence
   by making an architecture assumption.

The handoff is complete when the next phase can understand what was decided, why it matters, which
inputs support it, and how the result will be verified.
