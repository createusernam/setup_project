# Issue Tracker — PROJECT_NAME

GitHub Issues on repo: REPLACE_WITH_REPO_URL

## Label conventions

See `triage-labels.md` for full label set.

## Issue format

```markdown
## What
[One sentence: what is broken or missing]

## Why it matters
[Link to contract.json criterion or product_brief.md section]

## Steps to reproduce (for bugs)
1. ...

## Acceptance criteria
- [ ] [Testable condition]
- [ ] [Testable condition]

## Context
[Relevant files, module IDs, contract criterion IDs]
```

## Workflow

1. All incoming tasks → `needs-triage`
2. `/triage` → classifies to one of 5 canonical labels
3. `ready-for-agent` → agent picks up
4. Closed with commit reference: `Fixes #N`
