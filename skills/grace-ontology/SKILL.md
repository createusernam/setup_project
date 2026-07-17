---
name: grace-ontology
description: The GRACE annotation vocabulary — what MODULE_CONTRACT, FUNCTION_CONTRACT, BLOCK, LOG_ANCHOR and knowledge-graph tags mean, how code and architecture tiers relate, and how product intent is linked without embedding a product methodology. Read before writing or reviewing GRACE markup or extending the knowledge graph.
user-invocable: true
metadata:
  version: "1.2.0"
  track: "agent (in-code documentation — not the human visualization track)"
---

# GRACE Ontology — Portable Markup Vocabulary

GRACE is used here as a structured transfer format for code and architecture. It records purpose,
boundaries, dependencies, flows and verification links so another person or agent can navigate the
system without reconstructing those relationships from scratch.

GRACE does not define the project's product strategy, business ontology, or architecture method.
Those choices remain in `product_brief.md`, `contract.json`, ADRs and the user's design process.

## Enforcement

`setup-grace-lint` checks the code-level vocabulary. The `--profile autonomous`
profile requires the stricter function contracts and block-anchored logs. `/code-review-expert` and
`/build-loop` consume the same checked structure; `/scaffold` creates it before implementation.

## Tier 1: code-level vocabulary

| Concept | Markup | Required meaning |
|---|---|---|
| `MODULE` | file path/name | stable code unit identity |
| `MODULE_CONTRACT` | `START_MODULE_CONTRACT` | purpose, scope, dependencies |
| `FUNCTION_CONTRACT` | `START_CONTRACT: fnName` | purpose, inputs, outputs, side effects |
| `BLOCK` | `START_BLOCK_NAME` / `END_BLOCK_NAME` | named logical region, unique in the file |
| `LOG_ANCHOR` | structured log statement | module, function, block and correlation identifier |

Relations:

- a module has one module contract;
- a module contains zero or more named blocks;
- declared dependencies point to other modules or external systems;
- an exported function has a function contract when the active profile requires it;
- a log anchor identifies the block whose execution it proves.

This tier answers: what does this code unit do, what does it depend on, and where can its important
behavior be observed?

## Tier 2: architecture-level vocabulary

GRACE Full represents architecture in shared artifacts:

| Concept | Artifact | Core properties |
|---|---|---|
| `MODULE_NODE` | `knowledge-graph.xml` | id, name, type, status, purpose, path, dependencies, verification ref |
| `ANNOTATION` | `knowledge-graph.xml` | symbol name and purpose |
| `CROSS_LINK` | graph dependency/link | source, target, relation type |
| `WAVE` | `development-plan.xml` | implementation order and included modules |
| `WAVE_MODULE` | `development-plan.xml` | purpose, inputs, outputs, errors, interface, dependencies |
| `VERIFICATION_ENTRY` | `verification-plan.xml` | check linked to a module, flow or criterion |

Common module types:

`ENTRY_POINT | CORE_LOGIC | DATA_LAYER | UI_COMPONENT | UTILITY | INTEGRATION`

Relation types should use project-native, observable semantics such as `calls-api`, `queries-db`,
`publishes-event`, `renders-component`, or `validates-input`. Add a new relation only when its
meaning is documented and useful to graph consumers.

This tier answers: how do modules connect, in what order are they built, and how is each one
verified?

## Product intent and traceability

Product context remains in neutral pipeline artifacts:

```text
product_brief.md §1 scope/outcomes ──→ contract.json.scope
product_brief.md §7 journeys       ──→ contract.json.user_flow
product_brief.md §8 criteria       ──→ contract.json.criteria[]
contract + task plan               ──→ GRACE module/flow/verification refs
```

At project level, `development-plan.xml <scope>` may mirror `contract.json.scope`. At module level,
use stable references instead of copying product prose or inventing a business ontology:

```xml
<M-ACCOUNT NAME="AccountService" TYPE="CORE_LOGIC" STATUS="planned">
  <purpose>Own account creation and account state transitions</purpose>
  <path>src/accounts/service.ts</path>
  <depends>M-IDENTITY, M-DATA</depends>
  <journey-ref>product_brief.md#7-user-journey</journey-ref>
  <criterion-ref>c1-account-created</criterion-ref>
  <verification-ref>V-M-ACCOUNT</verification-ref>
</M-ACCOUNT>
```

The example demonstrates the shape only. Use the project's actual identifiers and terminology.

Optional references may include:

- `actor-ref` — an actor defined in the brief or context document;
- `journey-ref` — a stable journey step or flow identifier;
- `criterion-ref` — a `contract.json.criteria[]` identifier;
- `adr-ref` — a decision that constrains the module;
- `risk-ref` — a risk/threat/rollout item owned by another artifact.

References do not change evidence status. An assumption in `evidence-handoff.json` remains an
assumption when a module links to it.

## What GRACE does not decide

Do not encode these as universal GRACE semantics:

- who the product's users, buyers, owners, or operators must be;
- which discovery or product-development method was used;
- which architecture style or decomposition method must be selected;
- whether a product claim is validated;
- business concepts that exist only in one project's private vocabulary.

If a project needs domain-specific graph fields, define them in that project's ADR/schema and keep
the portable base vocabulary intact.

## Review checklist

- [ ] IDs are stable and unique.
- [ ] Purpose and scope describe responsibility, not implementation trivia.
- [ ] Dependencies and interfaces match the actual code/system boundary.
- [ ] Product links use stable actor/journey/criterion IDs.
- [ ] Verification references resolve to real checks.
- [ ] Domain-specific extensions are documented locally rather than presented as GRACE defaults.
- [ ] Human visualization artifacts remain separate from the agent knowledge graph.

## Summary

- Tier 1 documents and anchors code units.
- Tier 2 connects modules, flows, build order and verification.
- Product intent crosses the boundary through stable references to brief, contract, ADR and risk
  artifacts.

GRACE tells the next consumer what the system contains and how its parts connect. It deliberately
does not tell the user how to discover a product or choose an architecture.
