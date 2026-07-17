---
name: code-review-expert
description: "Expert code review of current git changes with a senior engineer lens. Detects SOLID violations, security risks, and proposes actionable improvements."
---

# Code Review Expert

## Overview

Perform a structured review of the current git changes with focus on SOLID, architecture, removal candidates, and security risks. Default to review-only output unless the user asks to implement changes.

## Severity Levels

| Level | Name | Description | Action |
|-------|------|-------------|--------|
| **P0** | Critical | Security vulnerability, data loss risk, correctness bug | Must block merge |
| **P1** | High | Logic error, significant SOLID violation, performance regression | Should fix before merge |
| **P2** | Medium | Code smell, maintainability concern, minor SOLID violation | Fix in this PR or create follow-up |
| **P3** | Low | Style, naming, minor suggestion | Optional improvement |

## Workflow

### 0) Contract check (v2.0+)

Before generic review, check for a feature contract:

```bash
test -f contract.json && test -f .contract-attestation \
  && [ "$(sha256sum contract.json | awk '{print $1}')" = "$(tr -d '[:space:]' < .contract-attestation)" ]
```

If a valid attested `contract.json` is present:

1. **Grade the diff against `contract.json.criteria`** as the primary review.
2. For each criterion:
   - Run `verify.command` if `verify.method` is `grep`/`test`/`typecheck`/`lint`/`build` — exit 0 = pass.
   - For `playwright` criteria: note that grading the live behavior is `/build-loop`'s job; here, statically check that the implementation could pass the playwright steps (e.g., the selectors exist, the handlers are wired).
   - For `api_contract` criteria: check the diff against the expected request/response shapes in `integrations.backend_endpoints`.
   - For `manual` criteria: render them as P2 findings for the human reviewer.
3. **must_pass failures are P0.** Any criterion with `must_pass: true` that doesn't pass blocks merge.
4. **Output contract-grade summary FIRST**, then continue with generic SOLID/security review.

Example contract-grade section in the output:

```markdown
## Contract Grade

**contract.json sha256**: abc123… ✓ attestation matches
**Criteria pass rate**: 18/23 (78%, weighted 0.81)
**must_pass failures**: 1 — c7-api-contract-400 (P0)

| ID | Pass | Score | Notes |
|----|------|-------|-------|
| c1-flow-happy-path | ✓ | 1.0 | playwright steps wired in src/routes/Goals.tsx |
| c7-api-contract-400 | ✗ | 0   | POST /api/goals returns 500 on negative amount, not 400 (api/routes/goals.ts:47) |
| ... |
```

If `contract.json` is missing or unattested, fall back to generic review (steps 1-6 below) and mention this in the output:

> No `contract.json` found. Falling back to generic SOLID/security/quality review. Consider running `/contract` first for contract-driven grading.

### 0b) GRACE Lite check — mechanical, runs before the human-judgment passes

```bash
setup-grace-lint --changed        # add --profile autonomous if /build-loop will run on this code
```

**Every error is P1** (block merge; P0 if the file is on a critical path — auth, payments, data writes).
Report them in their own section, before the SOLID pass, with the exact fix.

This is not style policing. GRACE Lite is declared mandatory for every file in the pipeline
(PIPELINE §GRACE Lite), and this review is the only place it gets checked mechanically. The rule
exists because the next agent to touch this file navigates by those anchors — an unmarked module is
one the agent will re-derive from scratch, wrongly. Same reasoning as dead code in step 3: what the
agent reads becomes its template.

Do not accept "it's a small file" or "the tests pass" as a reason to skip a MODULE_CONTRACT. If the
diff adds source files with no contract header, that is a finding, not a preference.

### 1) Preflight context

- Use `git status -sb`, `git diff --stat`, and `git diff` to scope changes.
- If needed, use `rg` or `grep` to find related modules, usages, and contracts.
- Identify entry points, ownership boundaries, and critical paths (auth, payments, data writes, network).

**Edge cases:**
- **No changes**: If `git diff` is empty, inform user and ask if they want to review staged changes or a specific commit range.
- **Large diff (>500 lines)**: Summarize by file first, then review in batches by module/feature area.
- **Mixed concerns**: Group findings by logical feature, not just file order.

### 2) SOLID + architecture smells

- Load `references/solid-checklist.md` for specific prompts.
- Look for:
  - **SRP**: Overloaded modules with unrelated responsibilities.
  - **OCP**: Frequent edits to add behavior instead of extension points.
  - **LSP**: Subclasses that break expectations or require type checks.
  - **ISP**: Wide interfaces with unused methods.
  - **DIP**: High-level logic tied to low-level implementations.
- When you propose a refactor, explain *why* it improves cohesion/coupling and outline a minimal, safe split.
- If refactor is non-trivial, propose an incremental plan instead of a large rewrite.

### 3) Removal candidates + iteration plan

- Load `references/removal-plan.md` for template.
- Identify code that is unused, redundant, or feature-flagged off.
- Distinguish **safe delete now** vs **defer with plan**.
- **Escalate dead/orphaned code to MUST-FIX severity** (not a generic nice-to-have): agents read existing code as few-shot examples, so dead code becomes a false template that propagates into new work. Deleting it is a correctness concern, not just hygiene.
- Provide a follow-up plan with concrete steps and checkpoints (tests/metrics).

### 4) Security and reliability scan

- Load `references/security-checklist.md` for coverage.
- Check for:
  - XSS, injection (SQL/NoSQL/command), SSRF, path traversal
  - AuthZ/AuthN gaps, missing tenancy checks
  - Secret leakage or API keys in logs/env/files
  - Rate limits, unbounded loops, CPU/memory hotspots
  - Unsafe deserialization, weak crypto, insecure defaults
  - **Race conditions**: concurrent access, check-then-act, TOCTOU, missing locks
- Call out both **exploitability** and **impact**.

### 5) Code quality scan

- Load `references/code-quality-checklist.md` for coverage.
- Check for:
  - **Error handling**: swallowed exceptions, overly broad catch, missing error handling, async errors
  - **Performance**: N+1 queries, CPU-intensive ops in hot paths, missing cache, unbounded memory
  - **Boundary conditions**: null/undefined handling, empty collections, numeric boundaries, off-by-one
- Flag issues that may cause silent failures or production incidents.

### 6) Output format

Structure your review as follows:

```markdown
## Code Review Summary

**Files reviewed**: X files, Y lines changed
**Overall assessment**: [APPROVE / REQUEST_CHANGES / COMMENT]

---

## Findings

### P0 - Critical
(none or list)

### P1 - High
1. **[file:line]** Brief title
  - Description of issue
  - Suggested fix

### P2 - Medium
2. (continue numbering across sections)
  - ...

### P3 - Low
...

---

## Removal/Iteration Plan
(if applicable)

## Additional Suggestions
(optional improvements, not blocking)
```

**Inline comments**: Use this format for file-specific findings:
```
::code-comment{file="path/to/file.ts" line="42" severity="P1"}
Description of the issue and suggested fix.
::
```

**Clean review**: If no issues found, explicitly state:
- What was checked
- Any areas not covered (e.g., "Did not verify database migrations")
- Residual risks or recommended follow-up tests

### 7) Next steps confirmation

After presenting findings, ask how to proceed only when the original request did not already fix the
mode. A read-only review ends with findings; an explicit fix request may proceed within its stated
scope. Otherwise use:

```markdown
---

## Next Steps

I found X issues (P0: _, P1: _, P2: _, P3: _).

**How would you like to proceed?**

1. **Fix all** - I'll implement all suggested fixes
2. **Fix P0/P1 only** - Address critical and high priority issues
3. **Fix specific items** - Tell me which issues to fix
4. **No changes** - Review complete, no implementation needed

Please choose an option or provide specific instructions.
```

**Important**: Do NOT implement any changes until user explicitly confirms. This is a review-first workflow.

When this review runs in pipeline Phase 7, also save the complete current review at root
`code-review.md`. Preserve the assessment (`APPROVE|REQUEST_CHANGES|COMMENT`), findings, checked
scope, commands/results, uncovered areas, and residual risks. Phase completion attests this stable
path before the human signs acceptance; a chat-only review cannot complete the pipeline.

## Resources

### references/

| File | Purpose |
|------|---------|
| `solid-checklist.md` | SOLID smell prompts and refactor heuristics |
| `security-checklist.md` | Web/app security and runtime risk checklist |
| `code-quality-checklist.md` | Error handling, performance, boundary conditions |
| `removal-plan.md` | Template for deletion candidates and follow-up plan |
