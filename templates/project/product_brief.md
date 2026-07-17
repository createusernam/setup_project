# Product Brief: [Product Name]

<!--
Portable handoff from product discovery to planning and delivery.
Methodology-agnostic: fill this with any discovery process or directly with stakeholders.
Keep claims aligned with evidence-handoff.json; do not present assumptions as validated facts.
Recommended size: no more than 200 lines.
-->

## Metadata

```yaml
product_name: ""
created: ""                 # ISO 8601
owner: ""                   # accountable person or team
product_type: ""            # software | service | physical | hybrid | other
delivery_format: ""         # web | mobile | API | offline | service | hybrid | other
is_frontend: null           # null during discovery; then true | false
is_backend: null            # null during discovery; then true | false
validation_stage: discovery # discovery | alpha | live
decision: alpha             # stop | alpha | delivery
status: draft               # draft | reviewed | pipeline-ready
```

## 1. Outcome and Scope

**Proposed product:** [one sentence: what may be built and for whom]

**Desired user outcome:** [the observable change for the intended user]

**Owner or business outcome:** [why the accountable person or organization is pursuing it]

**In scope:**

- [capability, workflow, user group, or boundary included]

**Not in scope:**

- [explicit exclusion and why it is excluded]

## 2. Users, Problem, and Evidence

**Primary users:** [people or systems that directly use the product]

**Other stakeholders:** [buyers, approvers, operators, affected parties, or external systems]

| Question | Current understanding | Evidence status/reference |
|---|---|---|
| What happens today? | [...] | [fact/hypothesis + ref] |
| What outcome is difficult to achieve? | [...] | [...] |
| Who experiences the problem and when? | [...] | [...] |
| How important or frequent is it? | [...] | [...] |
| What alternatives are used today? | [...] | [...] |

**Key assumptions:**

- [assumption that still needs testing]

**Open questions:**

- [question that could change scope, priority, or solution]

Detailed claim status, evidence ceilings, and falsifiers belong in `evidence-handoff.json`.
Material specification gaps also belong there. A blocking gap must name its owner and be answered,
tested with a semantic/technical prototype, accepted as a recorded risk, or moved out of scope
before planning or contract preflight can pass.

## 3. Proposed Product

Describe the proposal without prescribing implementation architecture.

**Value proposition:** [what useful outcome the product enables and for whom]

**Core capabilities:**

| Capability | User or system outcome | Priority |
|---|---|---|
| [...] | [...] | must / should / could |

**User contribution or prerequisites:** [what users must provide, know, or do]

**Known limitations:** [where the proposal is not expected to work]

## 4. Operating Model

| Aspect | Description |
|---|---|
| Delivery channel | [web, mobile, API, in-person, hybrid, etc.] |
| Owner/operator | [who runs and supports it] |
| Access and eligibility | [who can use it and under what conditions] |
| Commercial model | [free, paid, internal, unknown, not applicable] |
| Support or service needs | [human/operational dependencies] |

## 5. System Context

This section records boundaries and constraints for architecture work; it does not select an
architecture.

| Aspect | Description |
|---|---|
| Existing systems | [systems/components the product must coexist with] |
| External integrations | [APIs, providers, devices, partner processes] |
| Data involved | [data classes, sources, owners, retention constraints] |
| Identity and access | [actors, authentication, authorization] |
| Operational constraints | [availability, latency, volume, environments, support] |

High-level flow, if known:

```text
[Actor/source] → [product boundary] → [external system or outcome]
```

Unknown architecture choices stay marked as open questions for planning.

For multi-actor or branching behavior, create a readable flow plus textual use cases under
`docs/behavior/` from the project templates. Reserve sequence diagrams for local message-order
questions; the end-to-end flow remains an activity/swimlane view.

## 6. Constraints and Risks

| Type | Constraint or risk | Required response / owner |
|---|---|---|
| Legal/privacy/security | [...] | [...] |
| Safety or irreversible impact | [...] | [...] |
| Accessibility/inclusion | [...] | [...] |
| Technical/operational | [...] | [...] |
| Organizational/commercial | [...] | [...] |

## 7. User Journey

Steps must be observable enough to plan and verify.

**User job or goal:** [what the user is trying to accomplish, in plain language]

### 7.1 Primary Path

| Step | Actor action or trigger | Product/system response | Expected result |
|---|---|---|---|
| 1 | [...] | [...] | [...] |
| N | [...] | [...] | [observable outcome] |

### 7.2 Edge and Failure Cases

| Condition | Expected behavior | Recovery or fallback |
|---|---|---|
| [invalid input, dependency failure, interruption, no permission, etc.] | [...] | [...] |

### 7.3 Decision Points

| Decision | Who/what decides | Information needed | Possible outcomes |
|---|---|---|---|
| [...] | [...] | [...] | [...] |

## 8. Success Criteria

Use stable IDs. Criteria should describe outcomes or externally observable behavior; detailed test
commands and weights are added later in `contract.json`.

### 8.1 User Outcomes

- [ ] **[c1-user-outcome]** [measurable user outcome] — `must_pass: true`

### 8.2 Product and System Outcomes

- [ ] **[c2-core-behavior]** [core behavior and expected result] — `must_pass: true`
- [ ] **[c3-reliability]** [failure/recovery expectation]

### 8.3 Owner or Operational Outcomes

- [ ] **[c4-owner-outcome]** [business, operational, support, or governance outcome]

### 8.4 Out of Scope

- [item intentionally excluded from this delivery]

## 9. Pipeline Handoff

Minimum handoff:

- `product_brief.md` — this document;
- `evidence-handoff.json` — claim status, assumptions, falsifiers, open questions, decision and stage;
- supporting research links, if any.

Downstream mapping:

| Brief section | Consumer |
|---|---|
| §1 scope and outcomes | `task_plan.md`, `contract.json.scope` |
| §2 evidence and assumptions | `researcher`, `grill-with-docs`, risk review |
| §2 blocking specification gaps | semantic pipeline preflight before planning/contract |
| §3 capabilities | planning and contract criteria |
| §5 system context | architecture handoff and `contract.json.integrations` |
| §6 constraints and risks | ADRs, risk review, rollout plan |
| §7 journey | `contract.json.user_flow`, `pm-review` |
| §8 criteria/out of scope | `contract.json.criteria[]`, `pm-review` |

Next steps:

1. Resolve material factual gaps with `researcher` if needed.
2. Run `grill-with-docs` to align terminology and record decisions in `CONTEXT.md`/ADRs.
3. Create `task_plan.md`; architecture work consumes this brief through
   `docs/human/ARCHITECTURE-GUIDE.md`.
4. Run `pm-review`, then the contract and build gates selected by the risk tier.

Do not use `status: pipeline-ready` or `decision: delivery` to imply evidence that is not present in
`evidence-handoff.json`.
