---
name: grace-status
description: "Show the current health status of a GRACE project. Use to get an overview of project artifacts, codebase metrics, knowledge graph health, verification coverage, and suggested next actions."
---

Show the current state of the GRACE project, including whether it is safe to hand to a longer autonomous run.

When the optional CLI is available, prefer `grace status --path <project-root>` for the initial report. Use `grace status --with modules --path <project-root>` when project-level health is not enough and you need module summaries before deeper investigation.

## Report Contents

### 1. Artifacts Status
Check existence and version of:
- [ ] `AGENTS.md` — GRACE principles
- [ ] `docs/knowledge-graph.xml` — version and module count
- [ ] `docs/requirements.xml` — version and UseCase count
- [ ] `docs/technology.xml` — version and stack summary
- [ ] `docs/development-plan.xml` — version and module count
- [ ] `docs/verification-plan.xml` — version and verification entry count
- [ ] `docs/operational-packets.xml` — optional packet template version

### 2. Codebase Metrics
Scan source files and report:
- Total source files
- Files WITH MODULE_CONTRACT
- Files WITHOUT MODULE_CONTRACT (warning)
- Total test files
- Test files WITH MODULE_CONTRACT
- Total semantic blocks (START_BLOCK / END_BLOCK pairs)
- Unpaired blocks (integrity violation)
- Files with stable log markers
- Test files that assert log markers or traces when relevant

### 3. Knowledge Graph and Verification Health
Quick check:
- Modules in graph vs modules in codebase
- Any orphaned or missing entries
- Modules in verification plan vs modules in development plan
- Missing or stale verification refs
- Pending phases and steps that still need execution
- Autonomy blockers from `bash ~/.claude/scripts/grace-lint.sh --profile autonomous`

Run `bash ~/.claude/scripts/grace-lint.sh <project-root>` as a fast integrity snapshot and include any
relevant findings in the report. It ships with this setup (`scripts/grace-lint.sh`, linked by
`install.sh`) — no external CLI required.

If the report is specifically about autonomous execution readiness, also run
`bash ~/.claude/scripts/grace-lint.sh --profile autonomous <project-root>` and summarize blockers
versus warnings. That profile is exactly what `/build-loop` hard-gates on, so its output is the
readiness answer, not a proxy for it.

When the report needs focused navigation instead of raw artifact dumps, use `/grace-ask` — it walks
the knowledge graph and answers with citations into the artifacts.

### 4. Recent Changes
List the 5 most recent CHANGE_SUMMARY entries across source and substantive test files.

### 5. Suggested Next Action
Based on the status, suggest what to do next:
- If no requirements — "Define requirements in docs/requirements.xml"
- If requirements but no plan — "Run `/grace-plan`"
- If plan exists but verification is still thin — "Run `/grace-verification`"
- If plan and verification are ready but modules are missing — "Run `/build-loop` (autonomous) or `/tdd` (human-paced)"
- If drift detected — "Run `/grace-refresh`"
- If fast integrity signals are needed before deeper review — "Run `bash ~/.claude/scripts/grace-lint.sh <project-root>`"
- If one lint code needs direct remediation guidance — "Run `bash ~/.claude/scripts/grace-lint.sh --json`"
- If the next step is targeted investigation of one module or file — "Run `/grace-ask` (it navigates the knowledge graph and answers with citations)"
- If tests or logs are too weak for autonomous work — "Run `/grace-verification`"
- If autonomy blockers are present — "Run `bash ~/.claude/scripts/grace-lint.sh --profile autonomous <project-root>` and strengthen verification or packet quality before execution"
- If everything synced — "Project is healthy"
