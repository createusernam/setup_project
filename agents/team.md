# Agent Team Configuration

Team policy is capability-based. Concrete model selections live in project `model-bindings.json`.

## Principles

- Route work by required capability, not provider brand or model generation.
- Keep implementer, test-owner, and acceptor on distinct model IDs when the phase requires it.
- Use an isolated context for acceptance so generator history cannot bias evaluation.
- Record capability profile, runtime, and model ID in every handoff.
- Change bindings when availability/cost changes; change routing only when capability policy changes.

## Roles

### Orchestrator / architect

- Profile: `reasoning_high`
- Owns decomposition, architecture handoff, contracts, and consequential synthesis.
- Produces plans and decisions that trace to brief journeys and criteria.

### General reasoning agent

- Profile: `reasoning_balanced`
- Owns document alignment, visualization, issue slicing, and routine orchestration.

### Research worker

- Profile: `research_worker`
- Receives one bounded question and returns findings, sources, limitations, and confidence.
- Does not approve its own synthesis.

### Implementer

- Profile: `implementation_general` (or `implementation_ui` for UI-specialized work)
- Reads the issue/plan, contract, scaffold, and relevant GRACE anchors.
- Writes code and a handoff without changing locked boundaries silently.

### Test owner

- Profile: `review_test`
- Must resolve to a different model ID from the implementer in a collegium phase.
- Challenges implementation claims, adds/runs tests, and returns `AGREE` or `DISAGREE` with evidence.

### Acceptor / judge

- Profile: `review_acceptance`
- Uses an isolated context and, in collegium phases, a model ID distinct from implementer/test owner.
- Evaluates only against the contract/rubric and recorded evidence.

## Build collegium

```text
IMPLEMENTER (implementation_general or implementation_ui)
    ↓ code + handoff.json
TEST OWNER (review_test; distinct model_id)
    ↓ tests + AGREE/DISAGREE
ACCEPTOR (review_acceptance; distinct model_id; isolated context)
    ↓ PASS / CONDITIONAL / FAIL
```

`scripts/pipeline-preflight.sh 6 <project>` validates binding completeness and distinct model IDs.
The agent must additionally confirm its actual runtime/model matches its configured role.

## Handoff fields

```json
{
  "agent_role": "implementer | test-owner | acceptor",
  "capability_profile": "implementation_general",
  "runtime": "configured-runtime",
  "model_id": "provider/model-id",
  "task_ref": "issue or plan leaf",
  "goal_achieved": true,
  "done": [],
  "files_touched": [],
  "uncertain_about": [],
  "test_status": "pass | fail | not_run",
  "next_agent": "test-owner"
}
```

The profile explains why the model was selected; the model ID proves which concrete model ran.
