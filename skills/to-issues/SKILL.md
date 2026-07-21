---
name: to-issues
description: Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using tracer-bullet vertical slices. Use when user wants to convert a plan into issues, create implementation tickets, or break down work into issues.
---

# To Issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets).

The project issue-tracker owner and label vocabulary live in `docs/agents/issue-tracker.md` and
`docs/agents/triage-labels.md`. If either is unresolved, stop and ask for the tracker decision; do
not invoke an unrelated setup workflow.

## Process

### 1. Gather context

Read `contract.json` and `task_plan.md` from the project root if available. These define scope boundaries, acceptance criteria, and task decomposition. Work from whatever is already in the conversation context. If the user passes an issue reference (issue number, URL, or path) as an argument, fetch it from the issue tracker and read its full body and comments.

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code. Issue titles and descriptions should use the project's domain glossary vocabulary, and respect ADRs in the area you're touching.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Verify the derived breakdown

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Compare granularity, dependencies, HITL/AFK ownership, journeys, and criteria against the approved
`task_plan.md`, `contract.json`, and `viz_before_tickets` view.

- If the breakdown is a faithful derivation, publish without another questionnaire; the signed
  visualization gate is the approval.
- If it exposes a real upstream conflict or missing decision, stop and show the smallest delta with
  a recommendation. Return the change to the owning plan/contract/view, re-attest it, and invalidate
  downstream state before continuing.
- Never let an informal late answer silently override the contract.

### 5. Publish the issues to the issue tracker

For each verified slice, publish a new issue to the issue tracker. Use the issue body template below. These issues are considered ready for AFK agents, so publish them with the correct triage label unless instructed otherwise.

Publish issues in dependency order (blockers first) so you can reference real issue identifiers in the "Blocked by" field.

<issue-template>
## Parent

A reference to the parent issue on the issue tracker (if the source was an existing issue, otherwise omit this section).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

Avoid specific file paths or code snippets — they go stale fast. Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it here and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- A reference to the blocking ticket (if any)

Or "None - can start immediately" if no blockers.

</issue-template>

Do NOT close or modify any parent issue.

### 6. Write the machine handoff

Update root `issues-manifest.json` from its project template. Set `status` to `approved` only after
every published issue has a real ID, exactly one `pbs_leaf` (one PBS leaf), and traces to canonical
`US-*` IDs through non-empty `story_refs` or `technical_enabler_for`, plus contract criteria. Allowed issue
types are `HITL` and `AFK`; allowed manifest statuses are `draft` and `approved` (authoritative shape:
`issues-manifest.schema.json`). The next phase attests this stable file; a chat-only issue list is
not a Phase 5 output.
