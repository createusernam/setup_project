# Optional Kaeru memory adapter

Kaeru is retrieval memory, not pipeline truth. The authority order is:

`Git/setup artifact > named workctl task > Kaeru > runtime session`.

At session entry, read pipeline status first, then the explicitly named workctl task. Use Kaeru
`awake`, `overview`, `search`, or `drill` only for missing cognitive context. At session exit, write
only explicit candidate episodes, claims, experiments, lessons, or references with repository
provenance. Never store credentials, PII, or unapproved customer material.

Packets follow `templates/project/kaeru-memory-ref.schema.json`. Validate them with:

```bash
python3 scripts/kaeru-adapter.py validate .kaeru/<packet>.json
python3 scripts/kaeru-adapter.py promotion-check .kaeru/<packet>.json
```

`promotion-check` does not promote anything. It verifies that the memory is supported/settled and
has a Git SHA or artifact pointer. Promotion remains a separate write in the canonical artifact's
producer phase, followed by normal validation, attestation, and any human gate.

The supported pilot topology is one private local vault and one long-lived daemon per trusted
operator machine, with one initiative per stable repository ID. A physical vault has one RocksDB
writer; separate physical vaults therefore need separate services and ports. Back up the vault and
measure useful recall, stale-memory rate, and false-authority incidents before enabling shared
storage. Detailed deployment material belongs to the private operator docs and is structurally
excluded from the public projection.
