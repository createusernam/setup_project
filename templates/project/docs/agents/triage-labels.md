# Triage Labels — PROJECT_NAME

5 canonical GitHub labels. Every issue has exactly one at any time.

| Label | Meaning | Next action |
|-------|---------|-------------|
| `needs-triage` | Incoming, not yet classified | Run `/triage` |
| `needs-info` | Missing info to act on | Ask author, wait |
| `ready-for-agent` | Actionable, agent can start | Pick up in session |
| `ready-for-human` | Requires human decision | Review + decide |
| `wontfix` | Will not be addressed | Close with reason |

## State transitions (from /triage)

```
needs-triage → needs-info      (missing reproduction / clarity)
needs-triage → ready-for-agent (clear enough for autonomous fix)
needs-triage → ready-for-human (architectural decision required)
needs-triage → wontfix         (out of scope per contract.json.out_of_scope)
needs-info   → ready-for-agent (info provided)
needs-info   → wontfix         (no response after N days)
```

## Create labels on GitHub

```bash
gh label create needs-triage --color "#E4E669" --description "Not yet classified"
gh label create needs-info --color "#D4C5F9" --description "Missing information"
gh label create ready-for-agent --color "#0075CA" --description "Agent can start"
gh label create ready-for-human --color "#E99695" --description "Requires human decision"
gh label create wontfix --color "#FFFFFF" --description "Will not be addressed"
```
