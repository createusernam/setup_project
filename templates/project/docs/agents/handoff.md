# Handoff Protocol

Every agent call ends with a handoff. The next agent reads this file before starting.

**Why**: LLM natively thinks in state transitions (Belief State in residual stream). Handoff = Belief State transfer between agents. Without it, each agent starts blind.

---

## handoff.json — Schema

```json
{
  "version": 1,
  "timestamp": "ISO timestamp",

  "agent_role": "orchestrator | researcher | backend-implementer | frontend-implementer | test-owner | judge",
  "model_used": "claude-opus | deepseek-v4 | glm-5.2 | deepseek-flash | claude-sonnet",

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
| `model_used` | yes | Collegium auditing — verify different models per role |
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

### After IMPLEMENTER (DeepSeek V4 / GLM 5.2)

```json
{
  "agent_role": "backend-implementer",
  "model_used": "deepseek-v4",
  "collegium_verdict": "needs-review",
  "next_agent": "test-owner",
  "next_agent_goal": "Verify implementation against contract.json criteria. Run tests. Flag any issue in uncertain_about."
}
```

### After TEST OWNER (GLM 5.2)

```json
{
  "agent_role": "test-owner",
  "model_used": "glm-5.2",
  "collegium_verdict": "agreed | disagreed",
  "collegium_notes": "Disagreed: missing rate limit test. Implementation ignores burst scenario.",
  "next_agent": "orchestrator | implementer",
  "next_agent_goal": "If disagreed: implementer fixes issues listed in collegium_notes. If agreed: orchestrator reviews for acceptance."
}
```

### After JUDGE (Opus, isolated)

```json
{
  "agent_role": "judge",
  "model_used": "claude-opus",
  "collegium_verdict": "PASS | CONDITIONAL | FAIL",
  "collegium_notes": "CONDITIONAL: add integration test for token refresh flow.",
  "next_agent": "implementer | done",
  "next_agent_goal": "If CONDITIONAL: fix items in collegium_notes, re-submit for judge. If PASS: ready to ship."
}
```

---

## Collegium Health Check

A healthy collegium shows:
- `model_used` is different across implementer → test-owner → judge
- test-owner has at least one `collegium_note` (even "no issues found, all criteria met")
- `uncertain_about` is addressed by the next agent or escalated to human

Red flags:
- test-owner always `agreed` with no notes → collegium not functioning
- `uncertain_about` is empty in every handoff → agent overclaiming certainty
- same model in both `backend-implementer` and `test-owner` → swap one
