# Research-to-guide style: from evidence to a document people can use

> Canonical composition guide for turning a validated research artifact into a clear handbook, playbook, teaching guide, or decision guide without weakening its evidence.

## Contents

1. [The governing law](#1-the-governing-law)
2. [What changes and what must not](#2-what-changes-and-what-must-not)
3. [The reader contract](#3-the-reader-contract)
4. [The preservation ledger](#4-the-preservation-ledger)
5. [Choose one through-line](#5-choose-one-through-line)
6. [Pain-first chapter design](#6-pain-first-chapter-design)
7. [The dual readout](#7-the-dual-readout)
8. [Evidence inside narrative prose](#8-evidence-inside-narrative-prose)
9. [Application and prototype](#9-application-and-prototype)
10. [Genre variants](#10-genre-variants)
11. [Diagrams, tables, and code](#11-diagrams-tables-and-code)
12. [Voice and sentence-level style](#12-voice-and-sentence-level-style)
13. [Failure modes](#13-failure-modes)
14. [Final audits](#14-final-audits)

---

## 1. The governing law

**Transform the path through the evidence; do not transform the evidence.**

A research report is organized for verification: questions, methods, findings, counterevidence, confidence, sources. A guide is organized for use: a reader promise, a concrete failure, a mechanism, an application, and a next action.

The job is therefore not to shorten the research. It is to change the order in which the reader meets it. A readable sentence must never silently:

- promote a hypothesis to a result;
- hide a contradiction;
- remove a boundary;
- turn an analogy into a mechanism;
- detach a number from its source;
- make a prototype look like product validation.

## 2. What changes and what must not

| May change | Must remain invariant |
|---|---|
| section order | meaning of each claim |
| terminology, after one precise definition | evidence status |
| amount of explanation | counterevidence and threats |
| examples and diagrams | source-to-claim relationship |
| prose register | scope and non-goals |
| one prototype used as a through-line | distinction between observed and proposed |

The guide may be longer than the research when it adds the missing bridge between fact and use: examples, a worked trajectory, interfaces, data contracts, failure recovery, build phases, and tests. Repetition that does not add a bridge is still repetition.

## 3. The reader contract

Before outlining, answer four questions in one sentence each:

1. **Who acts?** Name the reader by role, not demographics.
2. **What can they do afterward?** Build, decide, explain, teach, or evaluate.
3. **What do they already know?** This controls jargon, not evidence depth.
4. **What is the output contract?** Separate MD, handbook, playbook, decision memo, prototype spec.

A useful opening makes a promise the document can actually keep:

> After this guide, you can build a vertical slice in which free language changes a world without giving the language model authority over that world's truth.

Avoid empty promises such as “you will understand everything” or “a comprehensive overview.”

## 4. The preservation ledger

The most dangerous stage is outlining from memory. Narrative fluency makes omissions feel intentional after the fact.

Build a ledger first:

| Item | Evidence status | Source | Destination | Treatment |
|---|---|---|---|---|
| load-bearing thesis | core | report §4 | chapter 1 | explain through failure |
| optional mechanism | hypothesis | report §8 | chapter 7 | benchmark and removal condition |
| cultural analogy | heuristic | report §10 | optional interface | label and ablate |
| limitation | threat | report §15 | boundary + evaluation | preserve verbatim meaning |

Map every major source heading. A merged item is acceptable only if the ledger records where its meaning went. An omission is acceptable only if the requested scope excludes it and the reason is explicit.

## 5. Choose one through-line

A long guide needs one situation that accumulates consequences. A new example in every chapter teaches vocabulary; one evolving example teaches a system.

The default progression is:

```text
reader promise
    → naive solution works
    → concrete failure appears
    → minimal fix introduces a new boundary
    → the boundary creates the next problem
    → all parts recombine in a prototype or decision
    → validation says whether to keep them
```

Good through-lines have:

- a visible stake;
- hard constraints;
- at least two legitimate outcomes;
- a failure that cannot be hidden by eloquent prose;
- enough depth to exercise every core mechanism.

Do not choose a flagship example merely because it is famous. Choose the smallest case that makes the important distinction impossible to fake.

## 6. Pain-first chapter design

Definitions answer “what is it?” Pain answers “why must I care?” A reader remembers the fix when they have first experienced the failure that forced its invention.

Use this loop where it fits:

### 6.1 The setup

Show the naive version that genuinely works under light conditions. The reader should think, “I would have done that.” A straw-man setup destroys trust.

### 6.2 The named failure

Give the failure a portable name: **beautiful lie**, **valid semantic error**, **branch explosion**, **poetic betrayal**. Then show a precise chain:

```text
cause → state change or misunderstanding → visible consequence → broken promise
```

The name is useful only if the scenario makes it concrete.

### 6.3 The real fix

Introduce the smallest mechanism that removes that failure. Show its contract, not just its brand or component name.

### 6.4 Why this layer is here

Explain ordering. What does this mechanism make possible? What new problem does its boundary expose? This sentence turns adjacent chapters into one argument.

### 6.5 Where it breaks

Every mechanism adds cost. State:

- the complexity it introduces;
- the condition under which it is unnecessary;
- how the system degrades when it fails;
- the fallback or removal rule.

Do not force appendices, source lists, schemas, or short connective sections into the full loop. Parallel structure is a reading aid, not a ritual.

## 7. The dual readout

For systems, services, methods, and games, connect experience to implementation:

| What the person experiences | What the system or operator does |
|---|---|
| “My words were understood” | parses free language into a typed proposal |
| “The other person may refuse” | checks authority and consent |
| “The world remembers” | records canonical events |

This prevents two common failures: an implementation guide with no user value, and a visionary guide with no mechanism.

Use the dual readout after the core promise and whenever a chapter contains several hidden technical steps. Do not repeat it mechanically if nothing new is revealed.

## 8. Evidence inside narrative prose

Use plain-language labels instead of flattening uncertainty:

- **Evidence-backed core:** supported strongly enough to build the first version.
- **Testable extension:** plausible, useful if it wins a named comparison.
- **Authorial heuristic:** a way to generate or visualize options, not an established causal model.
- **Unknown:** evidence is absent or premises are insufficient.

Place citations next to quantitative, current, and non-obvious claims. Use an annotated source appendix when inline citation density interrupts the explanation; each entry states what the source supports and what it does not.

Keep these distinctions explicit:

- syntax validity is not semantic correctness;
- benchmark performance is not product value;
- coherence is not causality;
- plausible output is not a canonical fact;
- correlation is not a guaranteed intervention effect;
- a small pilot discovers failures but does not confirm a broad effect.

## 9. Application and prototype

“This can be used in games” is not an application section. A prototype must operationalize the thesis.

Include:

1. **Promise:** what the user can do or experience.
2. **Actors and authority:** who controls which decisions.
3. **Hard facts and forbidden shortcuts:** what cannot be generated away.
4. **A complete trajectory:** input, interpretation, state transition, response, next options.
5. **A failure branch:** ambiguity, refusal, timeout, or invalid transition.
6. **Artifacts:** state, schemas, storylets, data, interface, or operational checklist.
7. **Build phases:** prove the deterministic core before generative polish.
8. **Evaluation:** tests, human measures, cost, and go/no-go gates.
9. **Non-claims:** what V0 deliberately does not prove.

The prototype should be the smallest case that can fail honestly. If the central thesis concerns consent, include a mixed utterance where the user controls one action but not another. If it concerns retries, include duplication. If it concerns decisions, include a real tradeoff and a rejected option.

## 10. Genre variants

Choose one primary genre. Do not mix unit loops casually.

| Genre | Unit | Loop | Repeated readout | Ending |
|---|---|---|---|---|
| Mentor/explainer | concept or mechanism | setup → named failure → fix → why → boundary | experience / mechanism | assembled prototype |
| Decision guide | option | context → evidence → tradeoff → why not → gateway | next action | recommendation |
| Field textbook | topic | pain → mechanics → diagram → good practice → failure → question | model answer | ranked question bank |
| Opportunity map | opportunity | proof → replicable example → local constraints → boundary | effort / payoff / channel / verdict | ranked openings |

The mentor pattern does not require fake autobiographical confessions. Use a personal mistake only when it is true and useful; otherwise name the common mistake directly.

## 11. Diagrams, tables, and code

Use a visualization only when the relationship is harder to retain in prose:

- three or more dependent stages → flow;
- repeated mappings → table;
- hierarchy or ownership → tree;
- state over time → timeline;
- UI layout → wireframe.

A diagram must answer a question. Introduce it with that question and interpret the one relationship the reader should notice. Do not restate every box afterward.

Code and schemas should expose a contract:

- input and output;
- authority boundary;
- invariant;
- failure or fallback.

Prefer a small real example over a large pseudocode wall.

## 12. Voice and sentence-level style

- Lead with the outcome, scene, or failure.
- Prefer concrete subjects and verbs: “the reducer rejects consent” over “validation is performed.”
- Explain a necessary English term once; then use it consistently.
- Keep a sober tone. “Promising” and “preliminary” are often more accurate than “revolutionary.”
- Vary paragraph length, but keep one causal move per paragraph.
- Use lists for contracts and choices, prose for causality and meaning.
- Put the reason next to the recommendation.
- Cross-link dependencies in long guides so chapters form a web.
- End major sections by creating the question the next section answers.

## 13. Failure modes

### Executive-summary collapse

Research is compressed to conclusions → mechanisms and limitations disappear → the reader cannot act or audit → readability is purchased with false certainty.

### Definition-first encyclopedia

Every chapter opens with terminology → the reader receives answers before feeling the question → retention and motivation collapse.

### Evidence dump

Citations are preserved but no reader journey is built → the output remains a research report with friendlier headings.

### Prototype theatre

A polished happy path is shown without authority, failure, or tests → the prototype cannot falsify the thesis → demonstration is mistaken for validation.

### Caveat fog

Every sentence is hedged → the reader cannot distinguish a strong result from an unknown → epistemic honesty becomes unusable. Use explicit evidence classes instead.

### Speculation smuggled by beauty

An elegant analogy improves the narrative → it is placed in the core architecture → later readers treat it as evidence. Keep heuristics optional and give them an ablation/removal condition.

### Parallel-structure ritual

Every section is forced into identical headings → simple material bloats and reference material becomes theatrical → the loop replaces judgment. Use the pattern for mechanisms, not every paragraph.

## 14. Final audits

### Coverage

- [ ] Every major input heading appears in the preservation ledger.
- [ ] Every ledger item has a destination, merge record, or explicit exclusion.
- [ ] Application and prototype satisfy every requested component.
- [ ] Source and baseline files remain unchanged when a separate output was requested.

### Epistemic integrity

- [ ] Core, extension, heuristic, and unknown remain distinguishable.
- [ ] Numbers and current facts have nearby sources.
- [ ] Counterevidence and threats remain visible.
- [ ] No prototype or schema is described as proof of product success.

### Reader utility

- [ ] The opening promises a concrete capability.
- [ ] One through-line accumulates across the document.
- [ ] Core mechanisms have named failure, fix, tradeoff, and boundary.
- [ ] The guide ends in an operational next action or assembled prototype.

### Markdown and delivery

- [ ] Code fences are balanced.
- [ ] Links, headings, and tables render correctly.
- [ ] No `TODO`, `TBD`, `FIXME`, or placeholder remains.
- [ ] The final response links the separate file and states what was validated.
