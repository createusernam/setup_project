# Product Brief: [Product Name]

<!--
Transmitter document — output of the product discovery phase.
Pipeline entry point. Methodology-agnostic: fill using any discovery process.

For МК-methodology integration: see ~/.setup/skills/methodology/SKILL.md
Mapping to contract.json: section 9.
Size limit: ≤200 lines (MODULE_CONTRACT rule).
-->

---

## Metadata

```yaml
product_name: ""
created: ""               # ISO 8601
creator: ""
product_type: ""          # product | service | program | community
delivery_format: ""       # digital | physical | service | hybrid
value_logic: ""           # chain | workshop | network
is_frontend: false
is_backend: false
problem_depth: ""         # surface | behavioral | identity
status: draft             # draft | pm-approved | pipeline-ready
```

---

## 1. Creator's Intent

*Why this is being built and what "done" means for the creator.*

**Building:** [one sentence — what product, for whom]

**Creator's success criteria:**
| Criterion | How measured |
|-----------|-------------|
| [result 1] | [metric] |
| [result 2] | [...] |

**Explicit non-goals** (scope boundary):
- [what this product will NOT do, and why]

---

## 2. Core Problem

*The problem the product resolves. Use the client's language, not theory.*

**Segment:** [who they are — described by activity, context, experience level]

| Aspect | Description |
|--------|-------------|
| Current state (what they do now) | [...] |
| Desired state (what they want) | [...] |
| Activating situation (when the tension surfaces) | [...] |

**False dichotomy** (what pulls in opposite directions):

The client acts as if they must choose between:
- Option A: `"[assumption required for current state]"`
- Option B: `"[incompatible assumption required for desired state]"`

Incompatibility: [why holding both simultaneously feels impossible — one sentence]

**Resolution** (what the product makes possible, in client language):
> "[Both options] are two ways to [express the same underlying thing]."
> *One sentence: what the client could say after the product works.*

**Problem depth:** surface / behavioral / identity  
Rationale: [what in the research indicates this level, not deeper/shallower]

---

## 3. Product

*What the product does, without discovery methodology terms.*

**Name and type:** [...]

**What happens for the client** (2–3 sentences, client perspective):
> [What the client does and what changes for them]

**Product mechanism:**
| Field | Value |
|-------|-------|
| Core operation | [what the product concretely does] |
| Entry point | [where the tension is engaged first] |
| Resolution path | [how the product moves client from false dichotomy to resolution] |

**Client's contribution:**
Client must: [what the client brings / does for the product to work]  
Without this: [what fails — critical for onboarding design]

---

## 4. Conditions of Exchange

*How the exchange is structured.*

| Parameter | Value |
|-----------|-------|
| Format | [online/offline, sync/async, group/individual] |
| Duration | [...] |
| Price / formula | [...] |
| Client entry point | [how client arrives] |

**Creator's capabilities** (why this creator, not another):
- [capability 1 — as operation, not abstract skill]
- [capability 2]

---

## 5. System Architecture

*Technical and operational picture. Source for integrations in contract.json.*

### 5.1 Product System

| Aspect | Description |
|--------|-------------|
| Type | digital / physical / service / hybrid |
| Key components | [what must be built / configured] |
| Data storage | [where and what is stored] |
| Integrations | [external systems] |

### 5.2 Data Flow

```
[Source] → [Processing] → [Storage] → [Delivery to client]
```

### 5.3 Client in the Exchange

| Aspect | Description |
|--------|-------------|
| Tools used | [interfaces / platforms] |
| What client brings | [data / context / materials] |
| What client leaves with | [results / artifacts / states] |
| Friction points | [where client may drop off] |

---

## 6. External Context

*What influences the exchange from outside.*

### 6.1 Client's Environment

| Question | Answer |
|----------|--------|
| What in their environment creates the tension? | [...] |
| What changes in their environment after the exchange? | [...] |
| What could neutralize the result? | [...] |

If problem_depth = identity: client's environment requires explicit modeling in design.

### 6.2 Market Context

| Aspect | Description |
|--------|-------------|
| Current alternatives | [what clients do instead] |
| Differentiator | [not a feature — the mechanism competitors don't use] |
| Unserved niche | [what tension the market leaves unresolved] |

### 6.3 Regulatory / Legal

[Licenses, GDPR/152-FZ, professional restrictions, etc. If none — "No material constraints."]

---

## 7. User Journey

*Source for user_flow in contract.json. Steps should be observable and testable.*

### 7.1 JTBD

```
"[Job To Be Done — what the client hires the product to do, in their words]"
```

### 7.2 Primary Path

| Step | Client action | Expected result |
|------|--------------|-----------------|
| 1 | [first contact] | [what they see / get] |
| 2 | [...] | [...] |
| N | [resolution moment — client experiences the false dichotomy dissolve] | [concrete artifact / state] |

Key principle: step N must correspond to the resolution statement from section 2.

### 7.3 Edge Cases

| Condition | Expected behavior |
|-----------|------------------|
| [what goes wrong] | [what product does] |
| [client not ready for their contribution] | [how onboarding handles it] |
| [client reverts to old state] | [what retains / what product does] |

### 7.4 Decision Points

[Where client may stop and what in the product keeps movement forward]

---

## 8. Success Criteria

*Source for criteria[] in contract.json. Must be measurable. Min 10, max 30.*

### 8.1 Client (resolution achieved)

- [ ] **[c1-resolution]** Client can [specific action] they couldn't before — `must_pass: true`
- [ ] **[c2-language]** Client articulates the resolution in their own words without prompting — `must_pass: true`
- [ ] **[c3-retention]** [Action repeats after N days / uses]
- [ ] **[c4-...]** [...]

### 8.2 Product (mechanism works)

- [ ] **[c5-core]** [Core function works] — `must_pass: true`
- [ ] **[c6-edge]** [Edge case handled]
- [ ] **[c7-data]** [Data persists / processes correctly]

### 8.3 Creator (exchange succeeded)

- [ ] **[c8-creator-1]** [Success criterion from section 1]
- [ ] **[c9-creator-2]** [...]

### 8.4 Out of Scope

```json
"out_of_scope": [
  "[Deep systemic problems beyond this product's mechanism]",
  "[Client's environment — modeled as context, not addressed]",
  "[Adjacent tensions in the segment — require separate product]"
]
```

---

## 9. Pipeline Mapping

*How this document connects to the setup pipeline.*

### Next step

```
Pass this file as context to /grill-with-docs:

"Here is the product brief for [name].
Run a grilling session: verify terminology, clarify domain,
find contradictions, produce CONTEXT.md and ADRs.
Problem depth: [surface/behavioral/identity].
Resolution mechanism: [one sentence from section 3]."
```

### Mapping table

| Section | Pipeline artifact | Destination |
|---------|------------------|-------------|
| 1. Creator's intent — scope | `contract.json.scope` | `/contract` |
| 2. Resolution | `user_flow.jtbd` | `/contract` |
| 7.2 Primary path | `user_flow.primary_path` | `/contract` |
| 7.3 Edge cases | `user_flow.error_paths` | `/contract` |
| 5.2 Data flow | `integrations.data_flow` | `/contract` |
| 5.1 Components | `integrations.backend_endpoints` | `/contract` |
| 8.1–8.3 Criteria | `criteria[]` | `/contract` |
| 8.4 Out of scope | `out_of_scope[]` | `/contract` |
| 2–3 (problem + product) | `CONTEXT.md` domain glossary | `/grill-with-docs` |
| 6 External context | `docs/adr/` external dependency decisions | `/grill-with-docs` |
| Metadata is_frontend / is_backend | contract flags | `/contract` Branch B |

### contract.json skeleton

```json
{
  "version": "2",
  "scope": "[from section 1 — creator's intent]",
  "created": "[ISO 8601]",
  "is_frontend": false,
  "is_backend": false,
  "is_architecturally_complex": false,
  "linked_issue": null,
  "linked_plan": "task_plan.md",
  "user_flow": {
    "jtbd": "[from section 2 — resolution]",
    "primary_path": [],
    "error_paths": []
  },
  "integrations": {
    "data_flow": "[from section 5.2]",
    "frontend_calls": [],
    "backend_endpoints": [],
    "schema_changes": [],
    "external_services": []
  },
  "criteria": [],
  "out_of_scope": []
}
```

---

## Notes and Open Questions

*Unconfirmed, unclear items to resolve in /grill-with-docs.*

- [ ] `UNCONFIRMED:` [open question 1]
- [ ] `UNCONFIRMED:` [open question 2]
- [ ] [What needs research before /contract]
