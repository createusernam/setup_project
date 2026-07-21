# Artifact and semantic-state contracts

`pipeline-machine.json` is the executable registry. `artifact_owners` binds phase-owned outputs to
producer phase(s), optional templates, media type, and schema. `artifact_contracts` covers
controller/project-owned or out-of-band artifacts such as model conformance, viewpoint, and Kaeru
packets.

For registered JSON artifacts:

1. producer writes bytes only in its owning phase;
2. `setup-pipeline attest` validates the registered schema before hashing;
3. the ledger records artifact SHA-256 plus schema path and schema SHA-256;
4. consuming preflight validates the current bytes again and rejects changed schema provenance;
5. skill-owned phase-process validators enforce semantic exit invariants beyond shape.

The portable validator in `scripts/json_schema.py` supports the bounded Draft 2020-12 vocabulary
used by committed schemas. Unsupported external references or formats fail closed.

## Phase 6 bounded-iteration chain

One PBS leaf remains traceable from canonical `task_plan.json`/generated `task_plan.md`, through
`issues-manifest.json` and `scaffold-manifest.json`, into `iteration-contract.json`, and finally into
`build-evidence.json` and `iteration-dashboard.json`. JSON is canonical; `dashboard.md` is a
deterministic human view and must never be maintained as a second state writer.

| Artifact | Producer | Schema / deterministic validator | Consumers |
|---|---|---|---|
| `issues-manifest.json` | Phase 5 `to-issues` | `issues-manifest.schema.json`; Phase 5 phase-process validator | scaffold, iteration contract |
| `scaffold-manifest.json` | Phase 5.5 `scaffold` | `scaffold-manifest.schema.json`; scaffold phase-process validator | iteration contract, integrity checker |
| `iteration-contract.json` | Phase 5.5 `scaffold` | `iteration-contract.schema.json`; `validate-iteration-contract.py` | worker boundary, budget/integrity checkers, Phase 6 validator |
| `iteration-budget.json` | trusted diff checker | `iteration-budget.schema.json`; `check-iteration-budget.py` | architect, evidence, dashboard, Phase 6 validator |
| `scaffold-integrity.json` | trusted integrity checker | `scaffold-integrity.schema.json`; `check-scaffold-integrity.py` | architect, evidence, dashboard, Phase 6 validator |
| `iteration-review.json` | trusted review orchestrator | `iteration-review.schema.json`; `validate-iteration-review.py` | evidence, dashboard, Phase 6 validator |
| `build-evidence.json` | trusted Phase 6 orchestrator | `build-evidence.schema.json`; `validate-phase6.py` | dashboard, Phase 7 |
| `iteration-dashboard.json` | visualization renderer | `iteration-dashboard.schema.json`; `render-iteration-dashboard.py --check` | generated `dashboard.md`, `SUPERVISION.md` link, Phase 7 human review |

The enforced sequence is worker → mechanical checks → architect → test owner → isolated acceptor.
The architect owns leaf/boundary and delta classification, but cannot replace independent testing or
acceptance. Any upstream byte change invalidates the registered downstream artifacts and their gates.

## Common state envelope

New cross-model exchange artifacts should use `templates/project/artifact-envelope.schema.json` as
their outer contract or map every equivalent field explicitly. It separates facts, assumptions,
unknowns, invariants, provenance, authority, revision, and legal-next-transition state. Legacy
artifacts are migrated per producer; do not wrap them mechanically if doing so would create a
second source of truth.

## Planning state

Planning uses a single writer: `task_plan.json`, `findings.json`, and `progress.json` are canonical;
their Markdown files are deterministic human views rendered by `planning-state.py`. Never edit both.

## Model capability evidence

`scripts/model-conformance.py` executes API golden scenarios and writes
`model-conformance/<provider>-<model>.json`. New project templates set conformance policy to
`required`; each enabled binding references matching evidence with a sufficient pass rate and
harness version. `scripts/opencode-conformance.py` supplies the equivalent isolated runtime adapter
for models available through an authenticated OpenCode provider; its filesystem tool evidence is
validated by the runner rather than accepted from model self-report. Runtime-managed temperature
or token limits are recorded as zero. Older binding files without the policy remain advisory until
deliberately migrated.

Credentials are accepted only from an environment variable, a hidden terminal prompt, or explicit
stdin. They are never written into artifacts, command output, model bindings, or review reports.
