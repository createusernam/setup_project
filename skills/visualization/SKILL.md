---
name: visualization
description: Render the human-track views at pipeline gates — the Mermaid plan diagram the human approves before tickets are cut (viz_before_tickets), module/dependency flowcharts, and the SUPERVISION.md index. Choose concern, then scale, then notation; never start from the tool. Separate from the agent GRACE track. Use between /judge and /to-issues or when the user asks to visualize a plan or architecture.
user-invocable: true
metadata:
  version: "1.1.0"
  track: "human (supervision) — the agent track is GRACE in-code markup"
---

# Visualization Guide — human-track views at pipeline decision points

Where the **human** sees what the AI is about to do, at the gates of `docs/human/PIPELINE.md`. This is the **human track** — the **agent** documentation track is separate (GRACE: in-code, not human-read; see `AGENTS.md`, `skills/grace-ontology/SKILL.md`). The two coexist and **do not render into each other**.

## Why (the risk this closes)

A plan can be internally consistent while omitting a requirement or adding an assumption. A compact
visual gives the human a reviewable view of scope, structure and dependencies before work is turned
into tickets. Mermaid is the default portable format, not a mandatory design method.

---

## Three rules

### Rule 1 — Choose concern and scale before notation

Start with the decision the view must support, then choose its scale, and only then select notation:

1. **Concern** — whose question and what decision? → `structural | behavioral | functional | data | goal`.
2. **Scale** — what altitude? black / gray / white box. **One diagram = one altitude**; mixing scales makes box size misrepresent system size.
3. **Notation** — only now pick the diagram language that encodes the chosen concern and scale.

### Rule 2 — The plan owner supplies the view before tickets

- **Who:** the person or agent responsible for the plan owns the view; a separate reviewer approves it.
- **When:** the view lands before work is committed to issues/build.
- **How:** save each view in a stably named Markdown file next to the state artifact.

### Rule 3 — Format by audience

| Format | Audience | Where viewed | Use |
|---|---|---|---|
| **JSON** | agent | state files | `contract.json`, `handoff.json` — keep agent-native, don't prettify |
| **Mermaid-in-Markdown** | human | any compatible Markdown renderer | primary portable gate format |
| **HTML** | human | **normal browser** | rich standalone review only. HTML is richer for viz and loads Mermaid via `<script src=".../mermaid@11/…min.js">` — in a browser the CDN works fine (**not** a claude.ai Artifact → no CSP block, no SVG pre-render). Colors inherit from `design-contract.json` `design_tokens.values.*` when present at project root, so Mermaid diagrams use the project's accent and near-black text. |

Switch: **≤2 diagrams → Markdown; ≥3 or needs interactivity → HTML.**

---

## Gate → view map

The concrete deliverable — for each human decision point in `docs/human/PIPELINE.md`, the concern drives cut → scale → notation:

| Gate | Human's concern | Cut | Scale | Notation |
|---|---|---|---|---|
| **-1 Discovery / PM** (`product_brief.md`) | are outcomes, users, scope and evidence status clear | goal | context | `mindmap` (goal tree); optional CLD when feedback dynamics matter |
| **2 + 2-PM** (`task_plan.md` / PBS) | does architecture trace to journeys/criteria; are risks visible | structural + behavioral | modules + end-to-end behavior | `mindmap` (PBS) + activity diagram/equivalent swimlane `flowchart` + module dependency `flowchart` |
| **3 Design HARD STOP** (wireframe) | does the UI match intent | structural + behavioral | components | wireframe (not Mermaid) + `stateDiagram-v2` (flows) |
| **4 + judge** (`contract.json` user_flow) | is "done" defined correctly | behavioral | scenario | `stateDiagram-v2` (step→expect = guarded transition, matches Playwright replay) + `journey` |
| **4b→5 "viz before tickets"** *(new gate)* | **what will the AI build, before issues** | structural + behavioral | modules | `flowchart` (module/dependency) + `kanban`/`flowchart` (issue breakdown, "blocked-by") |
| **7 Verify / review** | what did it *actually* build | structural | modules | `flowchart` from `knowledge-graph.xml` `<depends>` (or a **stack-native** dep tool — TypeDoc/Madge, **not** Doxygen — if a code-derived graph is ever needed) |

---

## The palette — reach past the usual 2-3

Mermaid offers several diagram types. Choose the smallest type that directly answers the review concern:

| Cut | Answers | Mermaid types |
|---|---|---|
| **Structural** | what exists, how connected | `flowchart` · `C4Context` · `architecture-beta` · `block-beta` · `classDiagram` · `erDiagram` · `mindmap` · `treeview-beta` |
| **Behavioral** | what after what, by trigger | `sequenceDiagram` · `stateDiagram-v2` · `journey` · `gitGraph` · `timeline` |
| **Functional / flow** | inputs→outputs, volumes | `flowchart` · `sankey-beta` |
| **Data** | how data is structured | `erDiagram` · `classDiagram` |
| **Goal / motivational** | why it exists, priorities | `mindmap` (goal tree) · `quadrantChart` · `requirementDiagram` · `radar-beta` · **CLD (no native type)** |
| **Quantitative / status** | shares, dates, board | `pie` · `xychart-beta` · `gantt` · `kanban` |

Bonus mappings to setup skills: `ishikawa-beta` (fishbone) → `/diagnose` cause analysis · `wardley-beta` → strategy · `packet-beta`/`zenuml`/`venn-beta` → niche.

### Behavior stack and readability budget

For software behavior, use the smallest projection that answers the current question:

1. end-to-end branches → UML activity view or an equivalent Mermaid flowchart with labelled
   swimlanes;
2. one actor goal → textual use case from `docs/behavior/use-case-template.md`;
3. one message-order hotspot → local `sequenceDiagram` linked to a numbered use-case step;
4. evaluator replay → `contract.json` actions, expects, errors, and trace anchors.

The textual use case is canonical; a diagram is a human-review projection. One diagram keeps one
concern and one altitude. Prefer 12–15 meaningful nodes. More than 20 nodes, more than 7 lifelines,
or nesting deeper than 3 means `SPLIT_REQUIRED` unless the owner records why the view remains
reviewable. This is an operational review budget, not a claim about the UML standard.

---

## The systems-dynamics gap (goal / dynamics cut)

Mermaid has no native type for causal-loop polarity (`+`/`−` edges and reinforcing/balancing
loops). When those dynamics materially affect a decision, use Graphviz DOT with signed edges or a
documented inline-SVG convention. Do not use causal-loop notation for an ordinary structural or
behavioral review.

---

## Obsidian supervision (no plugin)

- Each gate writes a **stably-named `*.md`** (not only inline JSON) with a ` ```mermaid ` block.
- One **`SUPERVISION.md`** index per project links the human-review artifacts.
- A **`.pipeline-state.json`** convention (current phase · last gate · open questions) lets Obsidian show "where the agent is" at a glance.

---

## HTML / Mermaid styling (design system integration)

When generating HTML for Mermaid gate reviews, pull the visual identity from
`design-contract.json` at the project root:

- `design_tokens.values.ink` → body text, axis labels, node text
- `design_tokens.values.accent` → flowchart boxes, state borders, journey scoring
- `design_tokens.values.accent2` → secondary lines, link arrows
- `design_tokens.values.warm_bg` → stateDiagram background fill

Inline CSS in the `<style>` block of the generated HTML — no external deps.
If `design-contract.json` is absent, fall back to the house defaults
(ink `#1c1c1c`, accent `#9a3b2f`, accent2 `#d98b6a`, warm_bg `#f6f1ee`).

---

## Anti-patterns

| ❌ | ✅ |
|---|---|
| Tool-first ("we have tool X — draw whatever it emits") | Concern first, then scale, then notation |
| Notation chosen before the stakeholder's question | Name the decision, then derive the view |
| Two scales on one diagram (service next to a single function) | One altitude per diagram |
| Executor draws the human view | Architect draws it; executor stays on the GRACE track |
| Visualize after tickets are cut | Visualize the plan **before** tickets |
| `flowchart`+`sequence` for everything | Pick the type that fits the cut (goal→`mindmap`/CLD, status→`kanban`, …) |
| One sequence diagram for the whole user journey | Activity/flow overview → textual use cases → local sequences only where message order matters |
