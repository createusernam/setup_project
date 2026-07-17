# Use Case: [UC-ID] [Actor goal]

```yaml
id: UC-...
goal: "observable actor outcome"
primary_actor: "actor-id"
trigger: "event that starts the scenario"
preconditions: []
main_success_scenario: []
alternate_flows: []
failure_and_recovery: []
postconditions: []
business_rules: []
evidence_refs: []
assumptions: []
open_questions: []
criterion_refs: []
```

## Local interaction view

Add a sequence diagram only when one fragment requires review of message order between actors,
components, or external systems. Link it to the numbered scenario step; do not redraw the entire
end-to-end flow.

## Executable mapping

| Scenario step | `contract.json` action/expect or integration reference |
|---|---|
| 1 | ... |
