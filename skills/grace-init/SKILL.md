---
name: grace-init
description: "Bootstrap GRACE framework structure for a new project. Use when starting a new project with GRACE methodology - creates docs/ directory, AGENTS.md, and XML templates for requirements, technology, development plan, verification plan, knowledge graph, and operational packet contracts."
---

Initialize GRACE framework structure for this project.

## Template Files

All documents MUST be created from template files located in this skill's `assets/` directory.
Read each template file, replace `$PLACEHOLDER` variables from approved project artifacts, and write
the result to the target project path. Do not turn missing architecture decisions into an intake
questionnaire; preserve them as pending for `/grace-plan`.

| Template source                          | Target in project           |
|------------------------------------------|-----------------------------|
| `assets/AGENTS.md.template`              | `AGENTS.md` (project root)  |
| `assets/docs/knowledge-graph.xml.template` | `docs/knowledge-graph.xml`  |
| `assets/docs/requirements.xml.template`    | `docs/requirements.xml`     |
| `assets/docs/technology.xml.template`      | `docs/technology.xml`       |
| `assets/docs/development-plan.xml.template`| `docs/development-plan.xml` |
| `assets/docs/verification-plan.xml.template`| `docs/verification-plan.xml` |
| `assets/docs/operational-packets.xml.template`| `docs/operational-packets.xml` |

> **Important:** Never hardcode template content inline. Always read from the `.template` files — they are the single source of truth for document structure.

## Steps

1. **Import project facts.** Read, in order when present:
   - `product_brief.md` and `evidence-handoff.json` for name, outcome, actors, journeys, constraints, evidence status, and critical flows;
   - `task_plan.md` and the architecture handoff for approved responsibilities, boundaries, risks, and verification needs;
   - existing `CLAUDE.md`, source manifests, test config, and logging config for implemented technology facts.

   Populate project name, annotation, keywords, UseCases, and critical flows from those sources.
   Populate runtime/framework/libraries/testing/observability only when already decided or observed.
   Otherwise mark the corresponding technology decision `pending` for `/grace-plan`; do not ask the
   product owner to invent it. If required brief or plan evidence is absent, halt and route to the
   owning phase instead of filling placeholders by interview.

2. **Create `docs/` directory and populate documents from templates:**

    For each `assets/docs/*.xml.template` file:
    - Read the template file
   - Replace `$PLACEHOLDER` variables with artifact-backed values or explicit `pending` markers
   - Write the result to the corresponding `docs/` path

3. **Create or verify `AGENTS.md` at project root:**
    - If `AGENTS.md` does not exist — read `assets/AGENTS.md.template`, fill in `$KEYWORDS` and `$ANNOTATION`, and write to project root
    - If `AGENTS.md` is a symlink — preserve it. Add only missing GRACE guidance to its canonical target when the approved write scope permits it
    - If `AGENTS.md` is a regular file — preserve existing rules and merge only non-duplicated GRACE guidance. Ask before replacing conflicting rules; never offer a blind overwrite

4. **Print a summary** of all created files and suggest the next step:
    > "Run `/grace-plan` to design modules, data flows, and verification references. Then deepen tests, traces, and log-driven evidence with `/tdd` + `/judge` before large execution waves. Use `docs/operational-packets.xml` as the canonical packet and delta reference during execution and refactors."
