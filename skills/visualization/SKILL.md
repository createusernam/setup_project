# Visualization Guide — human-track views at pipeline decision points

Where the **human** sees what the AI is about to do, at the gates of `docs/human/PIPELINE.md`. This is the **human track** — the **agent** documentation track is separate (GRACE: in-code, not human-read; see `AGENTS.md`, `skills/grace-ontology/SKILL.md`). The two coexist and **do not render into each other**.

## Why (the risk this closes)

> «Максимальный риск не в его ошибках, а в том, что мы просто не все требования предъявляем. ИИ как "мастер додумывания" добавляет самостоятельно компоненты решения, но всегда есть вероятность, что его "наиболее вероятно" лишь вероятно, но не правильно.» — quote file

So the human must **see the AI's intent before commitment**. «Читать [спеки и код] самих — бесперспективно, нужны визуализации класса bird's-eye view.» Mermaid is that bird's-eye control over AI decisions.

---

## Three rules

### Rule 1 — Notation is the LAST question (`разрез → масштаб → нотация`)

From `sistemy-celi-dinamika-guide-v2.md`. **Never start from the tool** ("we have Doxygen / BPMN / flowchart" → draw whatever it draws) — that is «нотация вперёд смысла», the classic failure: you describe what's convenient to draw, not what needs understanding. Start from the human's decision:

1. **Разрез (cut)** — whose concern, what decision? → `structural | behavioral | functional | data | goal`.
2. **Масштаб (scale)** — what altitude? black / gray / white box. **One diagram = one altitude** (правило одной высоты — mixing scales makes box-size lie about system size).
3. **Нотация** — only now pick the language (Mermaid type) that encodes the chosen cut+scale.

### Rule 2 — The Architect draws, and before tickets

- **Who:** the model that wrote the spec/plan (Architect), **not** the executor. «У меня делает Архитектор, агент-исполнитель уже 100% автоматический» — the executor's own docs are agent-tuned and unreadable by humans (that's the GRACE track).
- **When:** «Визуализация плана. **До тикетов.**» The view lands at the gate **before** work is committed to issues/build.
- **How (agent instruction pattern):** «сделать отдельным файлом модель сущности/связи в формате mermaid/md» — the agent emits each view as its own stably-named `*.md` next to the state file.

### Rule 3 — Format by audience

| Format | Audience | Where viewed | Use |
|---|---|---|---|
| **JSON** | agent | state files | `contract.json`, `handoff.json` — keep agent-native, don't prettify |
| **Mermaid-in-Markdown** | human | **Obsidian** (renders `mermaid` fences natively) | **PRIMARY** gate format. «Obsidian хорошо подходит для присмотра за агентами» |
| **HTML** | human | **normal browser** | rich standalone review only. HTML is richer for viz and loads Mermaid via `<script src=".../mermaid@11/…min.js">` — in a browser the CDN works fine (**not** a claude.ai Artifact → no CSP block, no SVG pre-render). Colors inherit from `design-contract.json` `design_tokens.values.*` when present at project root, so Mermaid diagrams use the project's accent and near-black text. |

Switch: **≤2 diagrams → Markdown; ≥3 or needs interactivity → HTML.**

---

## Gate → view map

The concrete deliverable — for each human decision point in `docs/human/PIPELINE.md`, the concern drives cut → scale → notation:

| Gate | Human's concern | Cut | Scale | Notation |
|---|---|---|---|---|
| **-1 Discovery / PM** (`product_brief.md`) | whose interest, what value system | goal | context | `mindmap` (goal tree); **+ CLD if value-loop dynamics matter** (see gap below) |
| **2 + 2-PM** (`task_plan.md` / PBS) | does arch trace to the user journey; ≥3 options scored | structural + behavioral | modules | `mindmap` (PBS) + `journey` (CJM) + `flowchart` (arch layers, dependency edges) |
| **3 Design HARD STOP** (wireframe) | does the UI match intent | structural + behavioral | components | wireframe (not Mermaid) + `stateDiagram-v2` (flows) |
| **4 + judge** (`contract.json` user_flow) | is "done" defined correctly | behavioral | scenario | `stateDiagram-v2` (step→expect = guarded transition, matches Playwright replay) + `journey` |
| **4b→5 "viz before tickets"** *(new gate)* | **what will the AI build, before issues** | structural + behavioral | modules | `flowchart` (module/dependency) + `kanban`/`flowchart` (issue breakdown, "blocked-by") |
| **7 Verify / review** | what did it *actually* build | structural | modules | `flowchart` from `knowledge-graph.xml` `<depends>` (or a **stack-native** dep tool — TypeDoc/Madge, **not** Doxygen — if a code-derived graph is ever needed) |

---

## The palette — reach past the usual 2-3

«Агенты сами применяют лишь 2-3 диаграммы из 26.» The 26 types grouped **by cut**, so the Architect picks the one that answers the concern:

| Cut | Answers | Mermaid types |
|---|---|---|
| **Structural** | what exists, how connected | `flowchart` · `C4Context` · `architecture-beta` · `block-beta` · `classDiagram` · `erDiagram` · `mindmap` · `treeview-beta` |
| **Behavioral** | what after what, by trigger | `sequenceDiagram` · `stateDiagram-v2` · `journey` · `gitGraph` · `timeline` |
| **Functional / flow** | inputs→outputs, volumes | `flowchart` · `sankey-beta` |
| **Data** | how data is structured | `erDiagram` · `classDiagram` |
| **Goal / motivational** | why it exists, priorities | `mindmap` (goal tree) · `quadrantChart` · `requirementDiagram` · `radar-beta` · **CLD (no native type)** |
| **Quantitative / status** | shares, dates, board | `pie` · `xychart-beta` · `gantt` · `kanban` |

Bonus mappings to setup skills: `ishikawa-beta` (fishbone) → `/diagnose` cause analysis · `wardley-beta` → strategy · `packet-beta`/`zenuml`/`venn-beta` → niche.

---

## The systems-dynamics gap (goal / dynamics cut)

Feedback loops and causal structure (`sistemy-celi-dinamika` ch. 7–10: обратные связи, архетипы, стоки-потоки) — **no native Mermaid type encodes causal-loop polarity** (the `+`/`−` on edges, reinforcing vs balancing loops). Fallback: **Graphviz DOT with signed edges**, or an inline-SVG convention.

**Justified only** at the discovery/goal gate where value-system dynamics are the actual concern — here `edinyy-podhod-3-metodologii.pdf` is the optional consult for the value-system view. **Do not force** systems-dynamics notation onto gates whose concern is structural or behavioral.

---

## Obsidian supervision (no plugin)

- Each gate writes a **stably-named `*.md`** (not only inline JSON) with a ` ```mermaid ` block.
- One **`SUPERVISION.md`** index per project links them — «проект контролируется… с помощью специально создаваемых для человека артефактов».
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
| Tool-first ("we have tool X — draw whatever it emits") | Concern-first: разрез → масштаб → нотация |
| Notation chosen before the stakeholder's question | Name the decision, then derive the view |
| Two scales on one diagram (service next to a single function) | One altitude per diagram |
| Executor draws the human view | Architect draws it; executor stays on the GRACE track |
| Visualize after tickets are cut | Visualize the plan **before** tickets |
| `flowchart`+`sequence` for everything | Pick the type that fits the cut (goal→`mindmap`/CLD, status→`kanban`, …) |
