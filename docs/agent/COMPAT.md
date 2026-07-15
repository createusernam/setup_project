# Cross-Runtime and Model Compatibility

The setup works across coding CLIs and provider APIs because durable artifacts, capability profiles,
and concrete model bindings are separate concerns.

## Three layers

| Layer | Owner | Changes when |
|---|---|---|
| transition semantics | `pipeline-machine.json` | the development process changes |
| capability/role policy | `model-routing.json` | a phase needs different capabilities or independence rules |
| provider/runtime/model selection | project `model-bindings.json` | the user changes provider, model generation, price, or availability |

Do not put concrete model names in routing policy. Do not edit the pipeline machine merely because a
provider renamed or replaced a model.

## Runtime matrix

| Feature | Agent-native CLI | General coding CLI | Terminal/API fallback |
|---|---|---|---|
| Skill invocation | native skill command/tool | name the skill or use installed discovery | paste/load `SKILL.md` explicitly |
| Parallel work | runtime agent primitive | runtime-dependent | human/orchestrator launches calls |
| Durable state | repository files | repository files | human saves returned artifacts |
| Cross-runtime continuation | `workctl` | `workctl` | `workctl resume` prompt |
| Human gates | explicit approval | explicit approval | human records signature |
| GRACE markup | agent edits files | agent edits files | human applies/reviews output |

Runtime differences affect invocation, not artifact contracts.

## Capability profiles

Canonical profiles live in `model-routing.json`:

| Profile | Intended capability |
|---|---|
| `reasoning_high` | difficult architecture, contracts, decomposition, consequential synthesis |
| `reasoning_balanced` | general orchestration, document work, issue slicing, visualization |
| `research_worker` | bounded evidence acquisition and source discipline |
| `implementation_general` | backend/data/API/general code with tools and test feedback |
| `implementation_ui` | frontend/interaction code and long UI context |
| `review_test` | independent test design and implementation challenge |
| `review_acceptance` | isolated artifact evaluation and final acceptance |

These are requirements, not provider recommendations. A single concrete model may satisfy several
profiles, except where a phase declares roles distinct.

## Configure concrete bindings

Each project has `model-bindings.json`, created from the project template:

```json
{
  "version": "1",
  "bindings": {
    "reasoning_high": {
      "runtime": "your-runtime",
      "model_id": "provider/model-id",
      "enabled": true
    },
    "implementation_general": {
      "runtime": "another-runtime",
      "model_id": "provider/code-model-id",
      "enabled": true
    },
    "review_test": {
      "runtime": "review-runtime",
      "model_id": "provider/reviewer-model-id",
      "enabled": true
    }
  }
}
```

Fill every profile used by the selected route. Unused profiles may remain unbound. Validate a phase:

### Allowed values

| Field | Allowed value |
|---|---|
| `version` | exactly `"1"` |
| binding key | one of the seven profile names in the capability table above; no extra keys |
| `enabled` | JSON boolean `true` or `false`; unused profiles stay `false` |
| `runtime` | `claude`, `codex`, `opencode`, `api`, `manual`, `self-hosted`, or `custom:<lowercase-slug>` |
| `model_id` | the exact non-empty, no-whitespace identifier selected by that runtime; use `provider/model-id` when the runtime uses that form |

`runtime` names the surface that will actually run the phase. `api` means a direct provider API;
`manual` means a human moves prompts/artifacts between surfaces; `self-hosted` means a locally
served model; `custom:<slug>` is the explicit extension point. Empty strings are valid only while
the binding is disabled.

Example shape (identifiers are placeholders, not recommendations):

```json
{
  "$schema": "./model-bindings.schema.json",
  "version": "1",
  "bindings": {
    "reasoning_high": {"runtime": "claude", "model_id": "provider/reasoning-model", "enabled": true},
    "reasoning_balanced": {"runtime": "codex", "model_id": "provider/general-model", "enabled": true},
    "research_worker": {"runtime": "api", "model_id": "provider/research-model", "enabled": true},
    "implementation_general": {"runtime": "codex", "model_id": "provider/code-model", "enabled": true},
    "implementation_ui": {"runtime": "opencode", "model_id": "provider/ui-model", "enabled": true},
    "review_test": {"runtime": "opencode", "model_id": "provider/test-model", "enabled": true},
    "review_acceptance": {"runtime": "claude", "model_id": "provider/review-model", "enabled": true}
  }
}
```

The adjacent `model-bindings.schema.json` is authoritative for shape. `model-check.sh` additionally
checks the profiles used by one phase and role independence.

```bash
bash ~/.claude/scripts/model-check.sh 2 /path/to/project
bash ~/.claude/scripts/pipeline-preflight.sh 6 /path/to/project
```

The scripts resolve profiles and enforce declared role separation. They cannot detect the model
currently generating a response, so the agent must compare its actual runtime/model identity with
the resolved binding and stop on mismatch.

## Independent roles

Different prompts or conversations on the same model ID provide context isolation, but they do not
satisfy a declared different-model collegium. When `distinct_roles` is present, each role must bind
to a different `model_id`.

Typical build flow:

```text
implementer (implementation_general)
  → handoff.json
test owner (review_test, different model_id)
  → tests + AGREE/DISAGREE
acceptor (review_acceptance, different model_id and isolated context)
  → final verdict
```

For artifact judgment outside a collegium, isolated context is still required even if the same
capability profile is reused later.

## Handoff model identity

Record both the logical role and resolved identity:

```json
{
  "agent_role": "implementer",
  "capability_profile": "implementation_general",
  "runtime": "your-runtime",
  "model_id": "provider/model-id",
  "task_ref": "issue-123",
  "done": [],
  "files_touched": [],
  "uncertain_about": [],
  "test_status": "not_run",
  "next_agent": "test-owner"
}
```

Never infer independence from display names alone. Compare the configured `model_id` values and keep
the acceptance context isolated from the generator context.

## Runtime configuration

Provider credentials, default models, and per-call overrides belong to the runtime's own config.
For example, a coding CLI may use:

```json
{
  "instructions": [
    "/absolute/path/to/setup/docs/human/PIPELINE.md",
    "/absolute/path/to/setup/docs/agent/COMPAT.md"
  ],
  "model": "provider/model-id",
  "small_model": "provider/fast-model-id"
}
```

Keep that runtime config consistent with project `model-bindings.json`. The binding file is the
pipeline declaration; the runtime config is what actually launches the model.

## Cross-runtime continuation

Use `workctl` when a task moves between CLIs:

```bash
workctl init auth-refresh --goal "Refresh auth"
workctl start auth-refresh --runtime runtime-a
workctl handoff auth-refresh --to runtime-b
workctl continue auth-refresh --runtime runtime-b
```

`workctl` transfers task state and artifact links, not hidden model context. See
`docs/human/WORKCTL.md`.

## Portable fallback

When no agent primitive exists:

1. resolve the phase profile with `model-check.sh`;
2. start the configured runtime/model manually;
3. load the relevant skill and required artifacts;
4. save the structured output to the expected state file;
5. use a separate configured model/context for review when required.

The pipeline remains portable as long as artifacts, semantic gates, and role independence are
preserved.
