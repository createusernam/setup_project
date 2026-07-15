# Handoff Protocol

Every agent call ends with a handoff. The next agent reads this file before starting.

**Why**: a durable handoff lets the next agent resume from explicit facts, decisions, uncertainty,
checks, and file references instead of reconstructing them from chat history.

---

## handoff.json — Schema

```json
{
  "version": 1,
  "timestamp": "ISO timestamp",

  "agent_role": "orchestrator | researcher | backend-implementer | frontend-implementer | test-owner | judge",
  "capability_profile": "implementation_general",
  "runtime": "configured-runtime",
  "model_id": "provider/model-id",

  "task_ref": "issue #N or PBS_LEAF_id",
  "goal_achieved": true,

  "done": [
    "implemented auth middleware (src/auth/middleware.ts)",
    "added MODULE_CONTRACT to all 3 files"
  ],

  "files_touched": [
    "src/auth/middleware.ts",
    "src/auth/middleware.test.ts"
  ],

  "uncertain_about": [
    "edge case: concurrent login from same user — test-owner should add concurrency test",
    "token expiry behavior when clock skew > 30s — needs product decision"
  ],

  "test_status": "pass | fail | not_run",
  "tests_run": ["src/auth/middleware.test.ts"],
  "test_failures": [],

  "collegium_verdict": "needs-review | agreed | disagreed",
  "collegium_notes": "",

  "grace_compliance": {
    "module_contracts": true,
    "start_end_blocks": true,
    "log_markers": true,
    "max_file_lines": 187
  },

  "next_agent": "test-owner",
  "next_agent_goal": "Verify auth middleware handles edge cases from uncertain_about. Write concurrency test.",

  "blocked_on": ""
}
```

---

## Fields Reference

| Field | Required | Notes |
|-------|----------|-------|
| `agent_role` | yes | Who produced this handoff |
| `capability_profile` | yes | Why this model was selected for the role |
| `runtime` | yes | Runtime/CLI used for the call |
| `model_id` | yes | Concrete configured identity; compare across distinct roles |
| `task_ref` | yes | Link to PBS leaf or GitHub issue |
| `goal_achieved` | yes | Boolean; if false, explain in `blocked_on` |
| `done` | yes | What was completed (human-readable, specific) |
| `files_touched` | yes | Exact file paths |
| `uncertain_about` | yes | Never leave empty without stating "nothing uncertain" explicitly |
| `test_status` | yes | `not_run` is valid; `pass` without test files is not |
| `collegium_verdict` | yes | `needs-review` after implementer; `agreed/disagreed` after test-owner |
| `grace_compliance` | yes | Self-reported; test-owner verifies |
| `next_agent` | yes | Role of next agent |
| `next_agent_goal` | yes | What the next agent should achieve (PCAM: goal not steps) |
| `blocked_on` | no | Product/human decision needed before next agent can proceed |

---

## Usage Per Role

### After IMPLEMENTER (`implementation_general` or `implementation_ui` binding)

```json
{
  "agent_role": "backend-implementer",
  "capability_profile": "implementation_general",
  "runtime": "configured-runtime",
  "model_id": "provider/implementation-model",
  "collegium_verdict": "needs-review",
  "next_agent": "test-owner",
  "next_agent_goal": "Verify implementation against contract.json criteria. Run tests. Flag any issue in uncertain_about."
}
```

### After TEST OWNER (`review_test` binding)

```json
{
  "agent_role": "test-owner",
  "capability_profile": "review_test",
  "runtime": "configured-review-runtime",
  "model_id": "provider/test-model",
  "collegium_verdict": "agreed | disagreed",
  "collegium_notes": "Disagreed: missing rate limit test. Implementation ignores burst scenario.",
  "next_agent": "orchestrator | implementer",
  "next_agent_goal": "If disagreed: implementer fixes issues listed in collegium_notes. If agreed: orchestrator reviews for acceptance."
}
```

### After JUDGE (`review_acceptance` binding, isolated context)

```json
{
  "agent_role": "judge",
  "capability_profile": "review_acceptance",
  "runtime": "configured-acceptance-runtime",
  "model_id": "provider/acceptance-model",
  "collegium_verdict": "PASS | CONDITIONAL | FAIL",
  "collegium_notes": "CONDITIONAL: add integration test for token refresh flow.",
  "next_agent": "implementer | done",
  "next_agent_goal": "If CONDITIONAL: fix items in collegium_notes, re-submit for judge. If PASS: ready to ship."
}
```

---

## Collegium Health Check

A healthy collegium shows:
- `model_id` is different across implementer → test-owner → judge when the route requires distinct roles
- test-owner has at least one `collegium_note` (even "no issues found, all criteria met")
- `uncertain_about` is addressed by the next agent or escalated to human

Red flags:
- test-owner always `agreed` with no notes → collegium not functioning
- `uncertain_about` is empty in every handoff → agent overclaiming certainty
- same model in both `backend-implementer` and `test-owner` → swap one
