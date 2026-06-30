# GRACE Ontology — Markup Vocabulary and Business Grounding

How the GRACE annotation system is structured in this setup, what it does and does not know about the business model from `product_brief.md`.

---

## What GRACE is in this setup

GRACE (Graph-RAG Anchored Code Engineering) is a structured annotation system that turns code into a navigable, verifiable graph. An LLM reading a GRACE-annotated file gets explicit purpose, scope, and dependency information without needing to infer it from code structure.

Two modes: **Lite** (mandatory, every file) and **Full** (optional, ≥2/4 criteria).

---

## The Ontology — Three Tiers

### Tier 1: Code-level (GRACE Lite — mandatory)

Vocabulary:

| Concept | Markup | Properties |
|---------|--------|-----------|
| `MODULE` | `// FILE: path` | path, name |
| `MODULE_CONTRACT` | `START_MODULE_CONTRACT` | purpose, scope, depends |
| `FUNCTION_CONTRACT` | `START_CONTRACT: fnName` | purpose, inputs, outputs, side_effects |
| `BLOCK` | `START_BLOCK_NAME` / `END_BLOCK_NAME` | name (unique in file), implicit scope |
| `LOG_ANCHOR` | log statement | module, function, block, correlationId |

Relations at this tier:
- MODULE has_contract → MODULE_CONTRACT
- MODULE contains → BLOCK*
- MODULE depends_on → MODULE* (declared in DEPENDS field)
- FUNCTION has_contract → FUNCTION_CONTRACT
- LOG_ANCHOR anchors_to → BLOCK

This tier answers: **what does this code unit do, what does it depend on, where are its logical boundaries**.

### Tier 2: Architecture-level (GRACE Full — optional)

Vocabulary:

| Concept | Artifact | Properties |
|---------|----------|-----------|
| `MODULE_NODE` | `knowledge-graph.xml` `<M-xxx>` | name, type, status, purpose, path, depends, verification-ref |
| `ANNOTATION` | `knowledge-graph.xml` `<fn-xxx>`, `<type-xxx>` | symbol name, purpose |
| `CROSS_LINK` | implicit in depends field | source module → target module, relation type |
| `WAVE` | `development-plan.xml` `<Wave>` | order, label, modules[] |
| `WAVE_MODULE` | `development-plan.xml` `<M-xxx>` | contract (purpose, inputs, outputs, errors), interface, depends, mental_tests |
| `VERIFICATION_ENTRY` | `verification-plan.xml` | linked to module via verification-ref |

Module types: `ENTRY_POINT | CORE_LOGIC | DATA_LAYER | UI_COMPONENT | UTILITY | INTEGRATION`

CrossLink relation types: `reads-config | queries-db | calls-api | renders-component | validates-input`

This tier answers: **how do modules form a graph, in what order do they get built, how is each verified**.

### Tier 3: Business context (currently partial)

This is where the value proposition touches GRACE.

| Concept | Where it lives now | Granularity |
|---------|-------------------|-------------|
| `MK_CONTEXT` | `development-plan.xml` `<mk_context>` | **project-level only** |
| `SCOPE` | `development-plan.xml` `<scope>` | **project-level only** |
| Roles (creator/customer/admin) | `product_brief.md` §1-2 | **not in GRACE markup** |
| Exchange phases | `product_brief.md` §4, §7 | **not in GRACE markup** |
| МК aspects (P1/P2/НТО) | `product_brief.md` §2 | **not in GRACE markup** |

**Current link from PB to GRACE:**

```
product_brief.md
  §1.2 scope  →  contract.json.scope  →  development-plan.xml <scope>
  §2.3 НТО   →  contract.json.user_flow.jtbd
  §8 criteria →  contract.json.criteria[]
  §2 МК      →  development-plan.xml <mk_context>  (project level)
                                     ↑
                        This is where the chain stops.
                        Module-level has no business annotations.
```

---

## What GRACE does and does not know

### Does know (current state)
- What each module does (purpose, scope)
- What each module depends on (structural)
- What logical blocks exist inside each module
- In what order modules should be built (waves)
- How each module will be verified (verification-ref)
- At project level: what МК the project addresses, what the scope is

### Does not know (current gap)
- Which **role** a module serves (creator? customer? both?)
- Which **exchange phase** it participates in (pre-exchange infrastructure, during-exchange core, post-exchange follow-up)
- Which **МК pole** it helps resolve (P1 facilitation, P2 facilitation, НТО bridge, creator tooling)
- Whether a module is **МК-critical** (removing it would break the НТО) or infrastructure

---

## What full business grounding would look like

If we extended the ontology to include VP business context at module level:

```xml
<!-- knowledge-graph.xml — annotated module entry -->
<M-TRANSFORM NAME="Transformer" TYPE="CORE_LOGIC" STATUS="planned">
  <purpose>Core product transformation logic</purpose>
  <path>src/transform/index.ts</path>
  <depends>M-CONFIG, M-DATA</depends>

  <!-- Business context annotations (currently missing) -->
  <serves_role>customer</serves_role>              <!-- creator | customer | admin | both | system -->
  <exchange_phase>during-exchange</exchange_phase>  <!-- pre | during | post | infrastructure -->
  <mk_aspect>nto-bridge</mk_aspect>                <!-- none | p1-facilitation | p2-facilitation | nto-bridge | creator-tool -->
  <mk_critical>true</mk_critical>                  <!-- true = removing breaks НТО -->

  <verification-ref>V-M-TRANSFORM</verification-ref>
</M-TRANSFORM>
```

This would let the knowledge graph answer questions like:
- "Which modules are МК-critical?" → `mk_critical=true` filter
- "What does the customer interact with during exchange?" → `serves_role=customer` + `exchange_phase=during-exchange`
- "What serves only the creator?" → `serves_role=creator`

### Source mapping (where annotations would come from)

| Annotation | Source in VP | Notes |
|-----------|--------------|-------|
| `serves_role` | §2 segment + §3.4 customer contribution + §5 systems | Roles come from who uses each part |
| `exchange_phase` | §4.1 format + §7.2 primary path | Map path steps to modules |
| `mk_aspect` | §2.2 P1P + §2.3 НТО + §3.2 transformer | The transformer module = `nto-bridge`; enablers = `p1/p2-facilitation` |
| `mk_critical` | §3.2 + §8 criteria `must_pass:true` | Modules whose `criteria[]` has `must_pass:true` linked items |

---

## Why the gap exists

The current GRACE ontology is **code-structural, not business-semantic**. This is deliberate for v1:

1. **Structural grounding is always correct** — purpose and dependencies don't change with business model evolution. Business grounding can become stale when МК analysis is revised.

2. **VP → contract.json → GRACE is the current bridge** — contract.json is the translation layer. Business context reaches GRACE at project level via `<scope>` and `<mk_context>`, not at module level.

3. **Module-level business grounding requires stable МК** — adding `mk_aspect` to modules before the МК is validated risks annotating based on wrong P1P. The pipeline runs `/judge` on VP before GRACE Full runs.

---

## Path to closing the gap (not yet implemented)

When the МК is validated and `contract.json` is sha256-locked, the `<mk_context>` in `development-plan.xml` is stable enough to annotate modules. The `/grace-plan` skill could:

1. Read `contract.json.user_flow` (НТО as JTBD)
2. Read `product_brief.md §2–3` (P1P, transformer, customer contribution)
3. For each module in `knowledge-graph.xml`: ask the orchestrator to assign `serves_role`, `exchange_phase`, `mk_aspect`
4. Flag `mk_critical=true` for any module whose removal would break a `must_pass:true` criterion

This would make the knowledge graph queryable by business intent, not just by technical structure.

---

## Summary

The GRACE ontology today has two active tiers:
- **Tier 1 (Lite)**: code-level — what each module/function/block does, verified at every file
- **Tier 2 (Full)**: architecture-level — how modules form a dependency graph, in what order they build

**Business context from the product brief enters at project level only** — via `<scope>` and `<mk_context>` in `development-plan.xml`. Roles (creator/customer/admin) and exchange system (pre/during/post exchange, МК poles) are **not yet annotated at the module level**.

The ontology answers *what the code does and how it connects*, not *whose job it serves or which МК pole it addresses*. Tier 3 (business grounding at module level) is a defined next step, pending stable МК validation.
