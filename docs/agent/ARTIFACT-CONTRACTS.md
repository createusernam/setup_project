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
