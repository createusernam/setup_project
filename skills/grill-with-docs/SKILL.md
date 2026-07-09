---
name: grill-with-docs
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, ADRs) inline as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions.
---

<what-to-do>

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

</what-to-do>

<supporting-info>

## Domain awareness

During codebase exploration, also look for existing documentation:

### File structure

Most repos have a single context:

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `CONTEXT-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

Create files lazily — only when you have something to write. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Scan for metamodel distortions

The user's statements hide missing requirements inside linguistic distortions. When you hear one, name it and ask the paired question — an unchallenged distortion is a requirement the agent will later "додумывает" on its own (full table: `docs/agent/PROMPT-FORMAT.md §Metamodel Distortion Check`).

| Distortion | Smell | Ask |
|---|---|---|
| Omission (passive) | "the feature needs to be built" | Who builds? For whom? What exactly? |
| Nominalization | "the implementation", "user onboarding" | Implement what? Onboard how? Which concrete actions? |
| Modal operator | "must", "can't", "should" | Who says? What happens if we don't? |
| Presupposition | "since users need X" | Do they? What's the evidence? |
| Omitted performative | "this is important" | To whom? Who decided? |
| Cliché | "best practices", "modern approach" | Which ones specifically? Why those? |
| False dichotomy | "should we A or B" | Is the either/or real, or is a third option hidden? |

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right there. Don't batch these up — capture them as they happen. Use the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

`CONTEXT.md` should be totally devoid of implementation details. Do not treat `CONTEXT.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Fold in business_model.md, if present

When `business_model.md` exists at project root (produced by your discovery process, Phase -1),
fold its business facts — segment, value, arguments — into `CONTEXT.md` as domain-glossary entries
so they survive downstream (they are not otherwise in the `product_brief.md → task_plan.md → …`
state chain, and the Architect phase reads `CONTEXT.md`, not `business_model.md`, by default). Do
this without carrying over the discovery process's own vocabulary — translate the business facts
into plain domain terms, the same way `product_brief.md` already does.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Use the format in [ADR-FORMAT.md](./ADR-FORMAT.md).

</supporting-info>
