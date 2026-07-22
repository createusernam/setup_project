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
| Same-runtime session affinity | `workctl --role` when supported | runtime-dependent | explicit session ID |
| Human gates | explicit approval | explicit approval | human records signature |
| GRACE markup | agent edits files | agent edits files | human applies/reviews output |

Runtime differences affect invocation, not artifact contracts.

Runtime skill discovery is equally structural: only a direct `skills/` child with a regular
`SKILL.md` is installable. `scripts/list-installable-skills.py` owns that set for the installer and
doctor; reference packages must never be registered by directory glob. OpenCode readiness requires
valid JSON whose `instructions` is an array containing the exact resolved `PIPELINE.md` and
`COMPAT.md` paths.

Executable browser adapters are versioned inputs. `toolchain-versions.json` owns the tested
Playwright MCP pin, committed command examples are checked against it, and a deliberate runtime
override is recorded as the resolved version in `build-evidence.json.tool_versions`.

Canonical pipeline documents therefore name portable skills without runtime punctuation. The only
translation table for Claude Code, Codex, OpenCode, and terminal/API invocation lives in
`../human/SETUP.md`. Run `setup-pipeline values` for allowed project values and exact schema-owner
paths; do not guess a provider model ID or copy a placeholder.

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

## Route by task signals, not role prestige

The phase profile is the minimum safe default. Before selecting a concrete binding, record the
task's `requirement_uncertainty`, `knowledge_rarity`, `interaction_density`, `fidelity_need`,
`reversibility`, and `cost_of_error` as low, medium, or high in the task plan, issue manifest, or
workctl context.

- High requirement uncertainty or cost of error calls for stronger synthesis, explicit gap
  resolution, and independent acceptance. A more fluent completion of a missing requirement is not
  evidence.
- High knowledge rarity or fidelity need can justify the most detail-capable model on the first code
  or UI pass. Generated code and tests may then let a cheaper compatible binding continue safely.
- High interaction density calls for long context and structured artifacts; first split behavior
  views that exceed the readability budget.
- Bounded, reversible, fully specified work with fast test feedback may use the cheapest enabled
  binding that satisfies the phase profile.

Do not route by labels such as “architect” or “coder” alone. Never use task signals to weaken a
phase's minimum capability, distinct-model rule, or isolated-review requirement. Canonical signal
definitions and selection rules live in `model-routing.json`.

## Configure concrete bindings

Each project has `model-bindings.json`, created from the project template:

```json
{
  "version": "1",
  "conformance_policy": {"mode": "required", "minimum_pass_rate": 0.8, "harness_version": "1"},
  "bindings": {
    "reasoning_high": {
      "runtime": "your-runtime",
      "model_id": "provider/model-id",
      "enabled": true,
      "conformance_ref": "model-conformance/provider-model.json"
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
| `conformance_ref` | project-relative `model-conformance/*.json`; required for enabled bindings when policy mode is `required` |

`runtime` names the surface that will actually run the phase. `api` means a direct provider API;
`manual` means a human moves prompts/artifacts between surfaces; `self-hosted` means a locally
served model; `custom:<slug>` is the explicit extension point. Empty strings are valid only while
the binding is disabled.

Example shape (identifiers are placeholders, not recommendations):

```json
{
  "$schema": "./model-bindings.schema.json",
  "version": "1",
  "conformance_policy": {"mode": "required", "minimum_pass_rate": 0.8, "harness_version": "1"},
  "bindings": {
    "reasoning_high": {"runtime": "claude", "model_id": "provider/reasoning-model", "enabled": true, "conformance_ref": "model-conformance/reasoning.json"},
    "reasoning_balanced": {"runtime": "codex", "model_id": "provider/general-model", "enabled": true, "conformance_ref": "model-conformance/general.json"},
    "research_worker": {"runtime": "api", "model_id": "provider/research-model", "enabled": true, "conformance_ref": "model-conformance/research.json"},
    "implementation_general": {"runtime": "codex", "model_id": "provider/code-model", "enabled": true, "conformance_ref": "model-conformance/code.json"},
    "implementation_ui": {"runtime": "opencode", "model_id": "provider/ui-model", "enabled": true, "conformance_ref": "model-conformance/ui.json"},
    "review_test": {"runtime": "opencode", "model_id": "provider/test-model", "enabled": true, "conformance_ref": "model-conformance/test.json"},
    "review_acceptance": {"runtime": "claude", "model_id": "provider/review-model", "enabled": true, "conformance_ref": "model-conformance/review.json"}
  }
}
```

The adjacent `model-bindings.schema.json` is authoritative for shape. `setup-model-check` additionally
checks the profiles used by one phase and role independence. Core preflight also validates required
conformance evidence: model ID, harness version, profile, pass rate, critical-probe coverage, and
qualified verdict. `implementation_general` and `implementation_ui` require `profile: coding_worker`;
one failed or missing critical probe blocks qualification even when aggregate pass rate exceeds 0.8.

Run a bounded API qualification without putting a key on the command line:

```bash
python3 scripts/model-conformance.py --provider PROVIDER --base-url BASE_URL \
  --model MODEL_ID --profile coding_worker \
  --output model-conformance/provider-model.json --api-key-stdin
```

For models reached through an already authenticated OpenCode provider, use the isolated runtime
adapter. It batches the structured-output probes into one request and independently verifies the
filesystem tool and multi-hop artifacts:

```bash
python3 scripts/opencode-conformance.py --model PROVIDER/MODEL \
  --profile coding_worker --output model-conformance/provider-model.json
```

The coding-worker critical set covers bounded patch/scope, compiler and targeted-test feedback,
scaffold preservation and contract-gap stopping, secret/destructive/hostile-content safety,
schema-valid handoff/dashboard input, and recovery after compiler/test failure. General conformance
remains available for non-implementation roles.

The credential is read from stdin (or the named environment variable) and is never written to the
result. A legacy binding file with no `conformance_policy` remains advisory until explicitly migrated;
new project templates fail closed.

Migration for an existing project is explicit and non-destructive:

1. keep the legacy file advisory while running conformance for each enabled model ID;
2. save the validated results under `model-conformance/`;
3. add each `conformance_ref` and the `conformance_policy` object in one reviewed edit;
4. run `setup-preflight` for every phase used by the selected route;
5. switch to `mode: required` only after all required bindings qualify.

Do not add an attestation bypass. Existing valid artifacts are revalidated on consume and receive
schema provenance on their next normal producer-phase attestation; schema-invalid legacy bytes must
be repaired rather than grandfathered.

```bash
setup-model-check 2 /path/to/project
setup-preflight 6 /path/to/project
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
worker → mechanical checks → architect → test owner → isolated acceptor
```

The worker uses the exact implementation binding. Trusted scripts own budget, scaffold, schema, and
evidence mechanics. The architect uses the exact reasoning binding and reviews one-leaf scope,
interfaces, requirements delta, debt delta, and whether explanations match evidence. The test owner
uses a different `review_test` model ID; the acceptor uses a third distinct `review_acceptance` model
ID in fresh isolated context. Context isolation never substitutes for distinct model IDs.

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

Same-runtime continuation is a separate optimization. For OpenCode, a task role can retain an exact
session/model/agent/variant binding:

```bash
workctl role-bind auth-refresh coder --runtime opencode \
  --session ses_abc123 --model provider/model-id --agent build --variant high
workctl continue auth-refresh --runtime opencode --role coder
```

This preserves prefix-cache affinity while durable files preserve recoverability. Fresh acceptance
and test-review roles must not reuse generator sessions. Session affinity does not weaken model-ID
separation, isolated-context, or single-writer lease requirements.

## Portable fallback

When no agent primitive exists:

1. enter the next applicable phase atomically with `setup-pipeline enter PHASE`;
2. resolve the phase profile with `setup-model-check` and confirm the actual runtime/model;
3. run `setup-pipeline guard PHASE` immediately before the first phase-owned write;
4. load the relevant skill and required artifacts; when it owns extra durable state, bind its
   trusted read-only validator once with `setup-pipeline set-process PHASE SKILL`;
5. save, validate, and attest the structured output from the producer phase;
6. run `setup-pipeline status` and return `continue_now`, `waiting_for_human`, or `complete`;
7. continue machine-owned work immediately, or reproduce the complete machine-rendered HumanRequest
   when named human authority is required; preserve its local evidence/instruction paths, exact
   file+schema or inline response format, allowed responses, consequences, and resume action;
8. use a separate configured model/context for review when required.

The pipeline remains portable as long as artifacts, semantic gates, phase-process validation, and
role independence are preserved. Every declared producer output must be a checked downstream input;
the machine contract rejects orphan outputs. `set-phase` remains only a deprecated atomic alias for
`enter`; it never restores the old mutation-before-validation behavior.

## Setup release documentation invariant

<!-- setup:public-projection-rule -->
When changing wider setup behavior, update its canonical public-safe rule in both `docs/human/` and
`docs/agent/` before publishing. If the change affects the engineering conveyor, update the
handbook's `setup-pipeline.html` only after `docs/human/PIPELINE.md`, then rebuild/validate the
handbook package. Commit the private source before running `publish-public.sh`; never repair drift
only in the generated public mirror. Private-only details remain in excluded owner paths.
