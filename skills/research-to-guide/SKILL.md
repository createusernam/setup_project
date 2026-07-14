---
name: research-to-guide
description: "Transform already validated research into a clear, evidence-faithful user guide without losing claims, limitations, sources, application, or prototypes. Owns reader contract, composition, narrative style, examples, prototype, and coverage audit. Use to rewrite, convert, expand, structure, or turn a research report, technical analysis, market study, domain review, literature review, findings file, or baseline document into a guide, playbook, handbook, tutorial, decision guide, or separate user-facing MD. Responsibility boundary: does not conduct the primary research and does not choose PDF typography/layout; use `researcher` before it and `guide-pdf` after it. Triggers: 'turn this research into a guide', 'make a user-friendly MD', 'переработай исследование в гайд', 'добавь применение и прототип', 'не потеряй важное'."
---

# Research to Guide

IRON LAW: NEVER IMPROVE READABILITY BY SILENTLY DROPPING A CLAIM, BOUNDARY, COUNTERARGUMENT, OR EVIDENCE STATUS.

Use this skill after research is complete or when the user provides a research artifact. It transforms evidence into a reader journey; it does not redo research unless a claim is missing, unstable, or explicitly challenged.

## Goal contract

`GOAL_ROOT`: Turn validated evidence into a guide the target reader can act on without changing claim meaning or evidence status.

- **Success:** the separate guide is operational, readable, source-traceable, and passes preservation coverage.
- **Not success:** a shorter or smoother report that silently drops boundaries, counterevidence, hypotheses, or unknowns.

## Usage

```text
/research-to-guide --source <research.md>
                   [--baseline <original.md>]
                   [--output <guide.md>]
                   [--genre mentor|decision|field-textbook]
                   [--prototype <name-or-path>]
```

- `source`: validated research or synthesis; required.
- `baseline`: earlier artifact to audit for content lost during research revision.
- `output`: always a separate Markdown file; infer `<source-stem>-guide.md` if omitted.
- `genre`: infer from the user's outcome if omitted.
- `prototype`: a concrete scenario that carries the explanation; derive one only when the evidence supports it.

## Workflow

Copy and track this checklist:

```text
Research to Guide Progress

- [ ] 1. Establish the evidence boundary ⚠️ REQUIRED
- [ ] 2. Build the preservation ledger ⛔ BLOCKING
- [ ] 3. Set the reader contract → PLAN_CONFIRM (conditional) ⚠️ REQUIRED
- [ ] 4. Compare composition architectures → SYNTHESIS_GATE ⛔ BLOCKING
- [ ] 5. Write the separate guide
- [ ] 6. Run evidence, coverage, and usability audits ⚠️ REQUIRED
- [ ] 7. Deliver the file and audit summary
```

## 1. Establish the evidence boundary ⚠️ REQUIRED

Read the source completely. If supplied, read the baseline and prototype materials completely enough to identify every load-bearing thesis, mechanism, limitation, and source.

Ask:

- What is supported well enough to recommend?
- What is a testable extension rather than a result?
- What is only an analogy, heuristic, or authorial choice?
- Which claims are time-sensitive and need fresh verification?
- What must remain explicitly unknown?

Do not begin prose while these categories are mixed.

## 2. Build the preservation ledger ⛔ BLOCKING

Create a working ledger before outlining:

| Item | Source location | Status | Reader destination | Preserve how |
|---|---|---|---|---|
| thesis / mechanism / limitation / source | section | core / hypothesis / heuristic / unknown | target chapter | explain / table / boundary / appendix |

Include every major heading from the source and baseline. Merge duplicates, but never delete one merely because it complicates the story. Record prototype requirements separately: player/user promise, constraints, full happy path, failure path, implementation, and validation.

Red flag: if the new outline was written before the ledger, discard the outline and return here.

Treat the ledger, reader contract, and selected composition as `GUIDE_STATE`. If work spans multiple turns, persist this state in the active planning artifact; do not rely on chat memory. Marker: `PRESERVATION_GATE` — no outlining until the ledger covers every load-bearing input section.

## 3. Set the reader contract

Infer or confirm:

- Who will act on this guide?
- What should they understand, decide, or build afterward?
- What prior knowledge may be assumed?
- What exact artifact did the user request?
- What is explicitly out of scope?

Apply `PLAN_CONFIRM` before drafting:

- If the user already specified audience, format, style, scope, and output, record `preapproved_by_request` in `GUIDE_STATE` and continue without asking again.
- If a missing choice would materially change the deliverable, present the reader contract, proposed output path, and assumptions; wait for approval.
- Do not ask questions whose answers are discoverable from the artifacts.

## 4. Design the through-line and chapter loop

Load `references/research-to-guide-style.md` now. Do not load it during raw evidence extraction: style must not distort the evidence boundary.

Before choosing a structure, generate at least three distinct composition architectures. If the genre is fixed, vary the through-line, ordering, or prototype—not the requested genre. Score each from 0.0–1.0 on:

- evidence preservation;
- reader utility;
- prototype or application fit;
- requested style and scope.

Select the highest-scoring architecture and record what each rejected option would explain better. Marker: `SYNTHESIS_GATE` — do not draft before this comparison.

For a mentor/explainer guide, prefer a through-line shaped like:

```text
reader promise → naive working setup → named failure → real fix
→ why this layer exists → where it breaks → next problem
```

Use one prototype or decision case across chapters when possible. For mechanisms, add the dual readout `what the user experiences / what the system or operator does`. A process with three or more dependent stages gets a diagram. Do not force every section into the loop when a source appendix, schema, or checklist is clearer.

## 5. Write the separate guide

Lead with the outcome and a concrete scene, failure, or decision—not a taxonomy. Explain unavoidable terms once, at first use.

For each recommended mechanism, state:

1. the failure it prevents;
2. how it works;
3. why it belongs at this point in the sequence;
4. the cost or tradeoff it adds;
5. its fallback or removal condition.

Carry evidence status in plain language. Keep citations next to supported claims; collect an annotated source appendix when inline density would interrupt the story. Expand examples and application where they improve understanding; do not pad the text with repeated summaries.

When a prototype is requested, include:

- promise, actors, constraints, and forbidden shortcuts;
- one complete trajectory plus at least one meaningful failure branch;
- state/data/contracts or operational artifacts;
- interface or user flow where relevant;
- phased build plan;
- tests, metrics, and go/no-go gates;
- what V0 deliberately does not prove.

## 6. Run three audits ⚠️ REQUIRED

### Evidence audit

- Every quantitative, current, or non-obvious claim has a supporting source.
- No hypothesis is phrased as an established result.
- No analogy is presented as a causal mechanism.
- Counterevidence and threats to validity remain visible.

### Coverage audit

Compare the guide to the preservation ledger and both input documents. Search explicitly for every load-bearing term. Every item is present, deliberately merged, or recorded as excluded with a reason.

### Usability audit

- The opening states the reader promise and shows why it matters.
- Chapters form one causal progression instead of an index.
- Named failures have concrete consequences.
- Diagrams replace only genuinely relational prose.
- Application, prototype, fallback, and next action are operational.
- Markdown fences, links, headings, and tables are valid.
- No `TODO`, `TBD`, `FIXME`, or placeholder remains.

## 7. Deliver

Return the clickable path to the separate guide and a compact handoff:

```yaml
status: success | conditional
output: path/to/guide.md
coverage: pass | gaps-listed
validation: [checks actually run]
excluded_by_scope: []
uncertain_about: []
```

Include size and any intentionally unresolved limitation. Do not require JSON-only output and do not make the user reconstruct the outcome from progress messages.

## Anti-patterns

- Executive-summary compression when the user asked not to lose information.
- Definition-first chapters that never show the pain that created the mechanism.
- A fresh example in every chapter; this destroys cumulative understanding.
- Turning every research caveat into timid prose; use explicit evidence labels instead.
- Citing a source list at the end without connecting sources to claims.
- Treating a valid schema, benchmark, or prototype as proof of semantic or product success.
- Adding an attractive speculative layer to the core because it improves the narrative.
- Rewriting the input file when the user requested a separate deliverable.

## Pre-delivery checklist

- [ ] Separate output file exists and source files are unchanged.
- [ ] `PRESERVATION_GATE` passed before outlining.
- [ ] `PLAN_CONFIRM` was satisfied explicitly or by the user's complete request.
- [ ] At least three composition architectures were compared before `SYNTHESIS_GATE`.
- [ ] Preservation ledger has no unhandled load-bearing item.
- [ ] Core, hypotheses, heuristics, and unknowns remain distinguishable.
- [ ] Requested application and prototype are complete, not just named.
- [ ] Each core mechanism has failure, fix, tradeoff, and boundary.
- [ ] Citations support the nearby claims.
- [ ] Markdown fences are balanced; no placeholders remain.
- [ ] Final response links the guide and reports validation.

`CRITICAL_REMINDER`: `PRESERVATION_GATE` before outlining. `PLAN_CONFIRM` before consequential drafting. `SYNTHESIS_GATE` before selecting one reader journey. Never trade evidence integrity for readability.
