# Structured Prompt Template

Copy and fill this template for any agent task.
Principles: see `~/.setup/PROMPT-FORMAT.md`

---

```xml
<prompt>
  <role>
    You are a [ROLE] with [N] years of experience in [DOMAIN].
    [Optional: relationship context — "Your partner is [USER], there is full trust."]
  </role>

  <context>
    Project: [PROJECT_NAME]
    Stack: [STACK]

    [PASTE RELEVANT FILES/CODE WITH GRACE MARKUP HERE]
    [Use MODULE_CONTRACT headers from actual files — inject inline, not as attachments]
  </context>

  <task>
    [ONE CLEAR GOAL. What needs to happen. Not HOW — WHAT.]
  </task>

  <constraints>
    <required>
      - [Must do 1]
      - [Must do 2]
      - [Must do 3]
    </required>
    <forbidden>
      - [Must NOT do 1]
      - [Must NOT do 2]
    </forbidden>
  </constraints>

  <think_before_answering>
    Before answering:
    1. Generate ≥3 hypotheses/approaches for this task
    2. Score each: [RELEVANT_CRITERIA] (0.0–1.0 each)
    3. Select highest scoring
    4. Include all in output.hypotheses[]
    5. Explain why selected is better than alternatives
  </think_before_answering>

  <output_format>
    Return ONLY valid JSON. No prose before or after.
    {
      "status": "success | error | needs_info | needs_approval",
      "data": {
        [TASK_SPECIFIC_FIELDS]
      },
      "confidence": 0.0,
      "hypotheses": [
        { "id": "h1", "description": "...", "score": 0.0, "evidence": [] },
        { "id": "h2", "description": "...", "score": 0.0, "evidence": [] },
        { "id": "h3", "description": "...", "score": 0.0, "evidence": [] }
      ],
      "selected_hypothesis": "h1",
      "issues": [],
      "trace": ["completed step 1", "completed step 2"],
      "next_action": "[what happens after this]"
    }
  </output_format>

  <critical_reminder>
    [SINGLE MOST IMPORTANT CONSTRAINT — repeat here for attention spike at end of context]
    Output must be valid JSON. No prose before or after.
  </critical_reminder>
</prompt>
```

---

## Quick reference: data fields by task type

### Research task

```json
"data": {
  "problem_validated": false,
  "core_tension": "...",
  "false_dichotomy": { "a": "...", "b": "...", "incompatibility": "..." },
  "resolution": "...",
  "problem_depth": "surface | behavioral | identity",
  "evidence": [],
  "language": { "exact_quotes": [], "key_metaphors": [] }
}
```

### Architecture/design task

```json
"data": {
  "decision": "...",
  "rationale": "...",
  "tradeoffs": [],
  "affected_modules": [],
  "adr": { "title": "...", "status": "proposed", "context": "...", "decision": "...", "consequences": "" }
}
```

### Code generation task

```json
"data": {
  "files_changed": [],
  "grace_contracts_updated": true,
  "tests_written": [],
  "log_markers_used": []
}
```

### Evaluation task

```json
"data": {
  "verdict": "PASS | CONDITIONAL | FAIL",
  "overall_score": 0.0,
  "criteria_scores": [],
  "blocking_issues": [],
  "recommendations": []
}
```
