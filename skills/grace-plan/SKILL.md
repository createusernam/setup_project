---
name: grace-plan
description: "Run the GRACE architectural planning phase. Use when you have requirements and technology decisions defined and need to design the module architecture, create contracts, map data flows, and establish verification references. Produces development-plan.xml, verification-plan.xml, and knowledge-graph.xml."
---

Run the GRACE architectural planning phase.

> **Architecture handoff (Phase 2b):** use `docs/human/ARCHITECTURE-GUIDE.md` for the required
> inputs, decisions, output fields and re-entry checklist. The user may choose any architecture
> method, tool or reasoning surface; this skill owns the GRACE artifact formats.

## Prerequisites
- `docs/requirements.xml` must exist and have at least one UseCase
- `docs/technology.xml` must exist; stack decisions may be `pending` on entry
- `docs/verification-plan.xml` should exist as the shared verification artifact template
- If requirements or the technology template are missing, tell the user to run `/grace-init` first
- If the verification plan template is missing, recreate it before finalizing the planning artifacts

## Architectural Principles

When designing the architecture, apply these principles:

### Contract-First Design
Every module gets a MODULE_CONTRACT before any code is written:
- PURPOSE: one sentence, what it does
- SCOPE: what operations are included
- DEPENDS: list of module dependencies
- LINKS: knowledge graph node references

### Module Taxonomy
Classify each module as one of:
- **ENTRY_POINT** — where execution begins (CLI, HTTP handler, event listener)
- **CORE_LOGIC** — business rules and domain logic
- **DATA_LAYER** — persistence, queries, caching
- **UI_COMPONENT** — user interface elements
- **UTILITY** — shared helpers, configuration, logging
- **INTEGRATION** — external service adapters

### Semantic Anchoring
Favor semantically rich module, function, flow, and block names.

- prefer names that carry domain meaning over abstract IDs or arbitrary placeholders
- make PURPOSE and SCOPE fields concrete enough that a worker can infer intent without guessing
- when a rule is subtle, include one or two compact examples in notes or verification scenarios instead of relying on a vague prose rule

### Reliability-First Stack Selection
Use `docs/technology.xml` to define an approved implementation stack for agents.

- name the preferred runtime libraries, test tools, logging stack, and framework surfaces explicitly
- note discouraged or non-default libraries when they would weaken autonomous reliability
- plan around tools and abstractions that the team is actually willing to verify and maintain

### Knowledge Graph Design
Structure `docs/knowledge-graph.xml` for maximum navigability:
- Each module gets a unique ID tag: `M-xxx NAME="..." TYPE="..."`
- Functions annotated as `fn-name`, types as `type-Name`
- CrossLinks connect dependent modules bidirectionally
- Annotations describe only the module's public interface
- Do not push private helpers or implementation-only types into shared XML artifacts

### Verification-Aware Planning
Planning is incomplete if modules cannot be verified.

For every significant module, define during planning:
- a `verification-ref` like `V-M-xxx`
- likely source and test file targets
- critical scenarios that must be checked
- the log or trace anchors needed to debug failures later
- which checks stay module-local versus wave-level or phase-level

## Process

### Phase 1: Analyze Requirements
Read `docs/requirements.xml`. For each UseCase, identify:
- What modules/components are needed
- What data flows between them
- What external services or APIs are involved

### Phase 1.5: Resolve Technology Decisions

Read constraints, existing manifests/source, operational environment, and approved architecture
handoff. Reuse implemented choices when they satisfy the requirements. For unresolved decisions,
propose 2-3 viable stacks and recommend one with explicit reliability, maintenance, verification,
cost, and reversibility trade-offs.

The product owner approves consequences and constraints. A named architect or technical reviewer
approves runtime/framework, data, testing, and observability choices. If the same person holds both
roles, record both authority scopes. Preserve `pending` when the evidence is insufficient; do not
ask an open-ended "what stack do you want?" question.

### Phase 2: Design Module Architecture
Propose a module breakdown. For each module, define:
- Purpose (one sentence)
- Type: ENTRY_POINT / CORE_LOGIC / DATA_LAYER / UI_COMPONENT / UTILITY / INTEGRATION
- Dependencies on other modules
- Key public interfaces (what the module exposes to other modules or callers)
- Tentative source path, test path, and `verification-ref`
- Semantic anchors the worker should reuse: module naming, function naming, and critical block names

Present this to the named architecture reviewer as a structured list. Ask only about unresolved
trade-offs that would change boundaries; otherwise record review without a new questionnaire.

### Phase 3: Design Verification Surfaces
Before finalizing the plan, derive the first verification draft:
- map critical UseCases to `DF-xxx` data flows
- assign `V-M-xxx` verification entries for important modules
- list the most important success and failure scenarios
- identify required log markers or trace evidence for critical branches
- note module-local checks plus any wave-level or phase-level follow-up
- define stop conditions or replan triggers for the highest-risk modules so execution can halt cleanly instead of drifting

Present this verification draft to the named test owner as part of the same review checkpoint. If
the verification story is weak, revise the architecture before proceeding.

### Phase 4: Mental Walkthroughs
Run "mental tests" for 2-3 key user scenarios step by step:
- Which modules are involved?
- What data flows through them?
- Where could it break?
- Which logs or trace markers would prove the path was correct?
- Are there circular dependencies?

Present the walkthrough to the architecture reviewer. If issues are found — revise the architecture.

### Phase 5: Generate Artifacts
After the named architecture reviewer and test owner approve their respective surfaces:

1. Update `docs/development-plan.xml` with the full module breakdown, public module contracts, target paths, observability notes, data flows, and implementation order. Use unique ID-based tags: `M-xxx` for modules, `Phase-N` for phases, `DF-xxx` for flows, `step-N` for steps, and `V-M-xxx` references for verification.
2. Update `docs/verification-plan.xml` with global verification policy, critical flows, module verification stubs, autonomy-gate evidence, and phase gates.
3. Update `docs/knowledge-graph.xml` with all modules (as `M-xxx` tags), their public-interface annotations (as `fn-name`, `type-Name`, etc.), `verification-ref` links, and CrossLinks between them.
4. Ensure `docs/technology.xml` explicitly names the preferred stack and observability surfaces the worker should stay inside.
5. Print: "Architecture approved. `verification-plan.xml` is written. Deepen tests/traces with `/tdd` + `/judge`, then run `scripts/pipeline-preflight.sh 6` to check execution readiness, and build via `/build-loop` (autonomous) or `/tdd` (human-paced)."

## Important
- Do NOT generate any code during this phase
- This phase produces ONLY planning documents and verification artifacts
- Every consequential architecture decision must have a named technical reviewer, rationale, and
  authority scope. Product-owner approval is required only when the trade-off changes product scope,
  user journey, cost/risk tolerance, or another product-owned constraint.

## Output Format
Always produce:
1. Module breakdown table (ID, name, type, purpose, dependencies, target paths, verification ref)
2. Data flow diagrams (textual)
3. Verification surface overview (critical flows, module-local checks, log or trace anchors, stop conditions)
4. Implementation order (phased, with dependency justification)
5. Risk assessment (what could go wrong, and what should stop or replan execution)
