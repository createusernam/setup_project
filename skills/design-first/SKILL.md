---
name: design-first
description: Wireframe-first frontend design flow: generate wireframe → human approval HARD STOP → derive API contract → save. Invoke when user says "design", "wireframe", "UI first", "design this screen", or starts frontend work.
---

# /design-first — Wireframe → API Contract → Design Gate

Design-first flow for frontend features. Forces wireframe agreement BEFORE API design and coding.

**Principle**: API is derived from UX, not the other way around.

## Usage

```
/design-first [feature-name]
```

## Phases

### Phase 1 — Wireframe Generation

Agent generates wireframe in structured markdown with:
- ASCII layout of key screens
- Component inventory
- User interactions (what happens on click/input)
- Data requirements per screen (what needs to come from API)

Uses design-prototyper agent persona.

```xml
<role>
You are a senior UX designer specializing in minimal, information-dense interfaces.
You follow Arutyunov IDS + Birman typography principles.
No decorative elements — every pixel must serve communication.
</role>
<context>
[product_brief.md §7 — user journey]
[design-contract.json if exists]
</context>
<task>
Create wireframe for [FEATURE] as structured markdown.
Include: screen layout, components, interactions, data-per-screen.
</task>
<constraints>
  <required>
    - Each screen: ASCII layout + data requirements table
    - Each interaction: explicit "User does X → System shows Y"
    - Data requirements: exactly what the API must return for this screen
  </required>
  <forbidden>
    - Decorative descriptions ("beautiful", "elegant")
    - Vague interactions ("user can interact with")
    - Leaving data requirements implicit
  </forbidden>
</constraints>
<output_format>
{
  "status": "needs_approval",
  "data": {
    "feature": "...",
    "screens": [
      {
        "name": "...",
        "layout": "ASCII string",
        "components": [],
        "interactions": [
          { "trigger": "...", "action": "...", "result": "..." }
        ],
        "data_requirements": [
          { "field": "...", "type": "...", "source": "api | local | computed" }
        ]
      }
    ]
  },
  "next_action": "Human approval required before API design"
}
</output_format>
```

### Phase 2 — Human Approval Gate

**Hard stop.** Present wireframe to user. Ask:

```
WIREFRAME READY FOR REVIEW:

[wireframe markdown]

Questions:
1. Does the user flow match product_brief §7 (user journey) primary_path?
2. Any missing screens or interactions?
3. Any data requirements that seem wrong?

Reply APPROVE to continue or describe changes needed.
```

Do NOT proceed to Phase 3 until explicit APPROVE.

### Phase 3 — API Contract Generation

From approved wireframe, derive minimal API contract.

```xml
<role>
You are a senior API designer. You design APIs backward from UI requirements —
only expose what the UI actually needs, nothing speculative.
</role>
<context>
Approved wireframe: [WIREFRAME_OUTPUT]
Tech stack: [from CLAUDE.md]
</context>
<task>
Design API contract from this wireframe.
For each screen's data_requirements, create the minimal API endpoint set.
</task>
<constraints>
  <required>
    - Every field in wireframe data_requirements must be covered by an endpoint
    - Endpoints must be named by resource, not by UI screen
    - Include request/response shapes with types
    - Include error cases the UI must handle
  </required>
  <forbidden>
    - Speculative endpoints not required by current wireframe
    - Vague types ("object", "any")
    - Missing error cases
  </forbidden>
</constraints>
<think_before_answering>
Generate 3 API design approaches (REST vs resource-oriented vs action-oriented).
Score each on: simplicity, coverage, future-proofness.
Select best, explain tradeoffs.
</think_before_answering>
<output_format>
{
  "status": "success",
  "data": {
    "api_version": "v1",
    "base_path": "/api/v1",
    "endpoints": [
      {
        "method": "GET|POST|PUT|DELETE|PATCH",
        "path": "...",
        "description": "...",
        "request": { "params": {}, "body": {}, "query": {} },
        "response": { "200": {}, "400": {}, "401": {}, "404": {}, "500": {} },
        "required_by_screens": []
      }
    ],
    "shared_types": {}
  },
  "hypotheses": [],
  "selected_hypothesis": "",
  "next_action": "Save as api-contract.json, then /contract"
}
</output_format>
<critical_reminder>
Every data_requirements field from the wireframe must be covered. Output valid JSON only.
</critical_reminder>
```

### Phase 4 — Save and Proceed

1. Save wireframe to `docs/wireframe-<feature>.md`
2. Save API contract to `api-contract.json`
3. Report to user:

```
✓ Wireframe: docs/wireframe-<feature>.md
✓ API contract: api-contract.json (<N> endpoints)

Next steps:
1. Run /design-rubric (if first UI feature for this project)
2. Run /contract with: inherits: ["design-contract.json", "api-contract.json"]
```

## Output

```json
{
  "status": "success",
  "data": {
    "wireframe_path": "docs/wireframe-<feature>.md",
    "api_contract_path": "api-contract.json",
    "endpoints_count": 0,
    "approved_by_human": true
  },
  "next_action": "/design-rubric (if first UI) or /contract"
}
```
