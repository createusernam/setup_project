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

## Numbered scenario and executable trace

Keep each step observable and short. Use the stable `UC-ID/step-N` anchor when a reader or IDE
agent needs the local context; do not make a sequence diagram carry the scenario itself.

| Step | Actor/system action | Criterion / contract path | Local interaction |
|---|---|---|---|
| 1 | ... | `C-...` / `contract.json#/...` | — |
| 2 | ... | `C-...` / `contract.json#/...` | `INT-...` only if message order is the question |

## Local interaction view

Add a sequence diagram only when one fragment requires review of message order between actors,
components, or external systems. Link it to one `UC-ID/step-N` and state the unresolved question;
do not redraw the entire end-to-end flow. Use `interaction-template.md` for the local artifact.

## Executable mapping

| Scenario step | `contract.json` action/expect or integration reference |
|---|---|
| 1 | ... |
