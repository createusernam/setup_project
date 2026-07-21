# Local Interaction: [INT-ID] [UC-ID]/step-[N]

## Review question

State one message-order question. Do not redraw the use case or the full flow.

## Traceability

- Use case: `[UC-ID]`, step `[N]`
- Flow: `FLOW-...`
- Contract path: `contract.json#/...`

## Local sequence view

```mermaid
sequenceDiagram
    participant Actor
    participant Component
    participant External
    Actor->>Component: trigger for step N
    Component->>External: only message order under review
    External-->>Component: response / failure
    Component-->>Actor: observable outcome
```

## Readability check

- One question and one use-case step, never an end-to-end retelling.
- More than 7 lifelines, 20 nodes, or nesting deeper than 3 requires `SPLIT_REQUIRED` and a justification in `behavior-index.json`.
