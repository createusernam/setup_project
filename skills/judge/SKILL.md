---
name: judge
description: LLM-as-Judge artifact evaluation with isolated evaluator context. Supports product-brief, contract, feature, and design types. Invoke when user says "judge this", "evaluate", "validate artifact", "check quality", or after completing any phase output. Plan approval belongs exclusively to pm-review.
---

# /judge — LLM-as-Judge Artifact Evaluation

Evaluates key artifacts against criteria using an isolated evaluator context. The evaluator has no access to the generator's reasoning — only the artifact and the rubric.

## Usage

```
/judge <artifact-type> [artifact-path]
```

Artifact types:
- `product-brief` — evaluates `product_brief.md`
- `contract` — evaluates `contract.json` completeness and quality
- `feature` — evaluates completed feature against `contract.json` criteria
- `design` — evaluates wireframe against `design-contract.json`

`plan` is intentionally not a generic judge type. `/pm-review` is the sole Phase 2 plan gate and
writes `pm-review.json`; do not create a second verdict for the same transition.

## Isolation principle

The judge **must not** be the same agent that created the artifact. Use a separate context:

```bash
# Claude Code: fork a new agent for evaluation
Task({
  subagent_type: "general-purpose",
  prompt: "You are an evaluator agent. Your only job is to score artifacts against rubrics..."
})
```

## Instructions (evaluator agent)

### System prompt for evaluator

```xml
<role>
You are a strict evaluator with 10+ years of product and engineering review experience.
You were NOT involved in creating the artifact. You have no bias toward approving it.
Your job: find gaps, not validate effort.
</role>
<constraints>
  <required>
    - Score each criterion 0.0–1.0 with specific evidence
    - List all issues, even minor ones
    - Verdict: PASS (all must_pass ≥ 0.7), CONDITIONAL (some issues), FAIL (must_pass < 0.7)
  </required>
  <forbidden>
    - Giving benefit of the doubt without evidence
    - Approving incomplete artifacts
    - Skipping criteria
  </forbidden>
</constraints>
```

### Rubric by artifact type

#### product-brief

Criteria (score each 0.0–1.0):
- `pb-problem-clarity`: Current problem and desired outcome are clear in user/stakeholder language
- `pb-scope-concrete`: Scope is testable, not aspirational
- `pb-user-journey-complete`: User journey has ≥3 concrete steps
- `pb-language-authentic`: Uses user's language, not theory terms
- `pb-proposal-concrete`: Proposed capabilities and boundaries are concrete, not vague "help"
- `pb-evidence-honest`: Facts, assumptions and open questions retain their evidence status
- `pb-criteria-testable`: §8 criteria are observable/testable
- `pb-pipeline-ready`: §9 handoff and evidence-handoff references are complete and consistent

**PASS threshold**: all must_pass criteria ≥ 0.7

#### contract

Criteria:
- `c-scope-clear`: scope is one sentence, testable
- `c-user-flow-complete`: primary_path has ≥3 steps, each Playwright-replayable
- `c-integrations-filled`: data_flow and endpoints are concrete
- `c-criteria-count`: ≥10 criteria
- `c-must-pass-coverage`: must_pass=true covers the core product outcome and primary transformation
- `c-no-manual-must-pass`: no must_pass criterion with verify.method = "manual"
- `c-attested`: sha256 attestation present

**PASS threshold**: all must_pass ≥ 0.8

Visualization is the next transition after contract PASS. It is evaluated by the human
`viz_before_tickets` gate, not by the contract rubric.

#### feature

Compare completed feature against `contract.json.criteria[]`:
- For each criterion: PASS / FAIL / PARTIAL
- Overall verdict if all must_pass criteria PASS

### Output format

```json
{
  "status": "success",
  "data": {
    "artifact_type": "...",
    "verdict": "PASS | CONDITIONAL | FAIL",
    "overall_score": 0.0,
    "criteria_scores": [
      {
        "id": "...",
        "score": 0.0,
        "must_pass": false,
        "verdict": "PASS | FAIL | PARTIAL",
        "evidence": "...",
        "gap": "..."
      }
    ],
    "blocking_issues": [],
    "recommendations": []
  },
  "confidence": 0.0,
  "hypotheses": [
    { "id": "h1", "description": "artifact is ready", "score": 0.0 },
    { "id": "h2", "description": "needs minor fixes", "score": 0.0 },
    { "id": "h3", "description": "fundamental gaps present", "score": 0.0 }
  ],
  "selected_hypothesis": "",
  "next_action": ""
}
```

### After evaluation

- **PASS**: proceed to next pipeline step
- **CONDITIONAL**: fix blocking_issues, re-run `/judge`
- **FAIL**: return to artifact creation phase, specific gaps listed

Write the current pipeline result to a stable root path:

- `contract` → `judge-report.json`;
- `feature` → `feature-judge-report.json`;
- `product-brief` or `design` outside a machine transition →
  `docs/judge-reports/<artifact-type>-<timestamp>.json`.

An optional timestamped archive may accompany a stable pipeline report, but it never replaces the
path required by the next preflight. Verdict values are `PASS|CONDITIONAL|FAIL`.
