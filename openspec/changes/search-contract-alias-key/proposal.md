# Proposal: search-contract-alias-key

Issue: #884

## Why

Issue #652 moved the attribution-exception map into DATA
(`measurement_model_aliases` on a model row), but the map can only be recorded by
a human hand-editing `data/models.json` after reading an ingest refusal:
`data/search_contract.json` never declared the key and its model-item schema is
`"additionalProperties": false` — a raw search snapshot that legitimately states
an exception (a co-branded fork, a vendor-variant row) has that key PRUNED
SILENTLY at the search stage, exactly the class AGENTS.md §2 rule 3b warns about
("a field the search asks for but the contract refuses is dropped SILENTLY").

## What Changes

- `data/search_contract.json` declares the same optional model-item key
  `measurement_model_aliases` (array of store model ids, unique, min 1) —
  additive, never `required`, `additionalProperties: false` kept (rule 3b/6b).
- `scripts/validate.py::check_measurement_alias_map` (mapping stage, already
  wired) ALSO reads the `data/raw/*.json` snapshots: a counterpart that is not a
  model id in the store fails the gate, naming BOTH sides — the snapshot file,
  the raw model, the dangling counterpart, and the store it must resolve in. A
  dangling exception can no longer sit in a raw snapshot until a later merge
  discovers it.
- `scripts/update_trending.py` carries a captured exception through INGEST
  additively: a NEW model row keeps the key it captured (`normalize_model`
  copies the row), and an EXISTING store row gains a dedicated
  `merge_measurement_aliases` seam — the union of counterparts, deduped, never
  narrowed (rule 3b), so a capture can fill the exception on a row a human has
  not touched.
- Tests in the same change (rule 6b): the Done-when replay — a raw snapshot
  carrying a RESOLVABLE exception conforms to `make validate --only search`,
  flows through the real ingest onto new AND existing rows, and a DANGLING one
  is refused by the mapping gate naming both sides.

## Impact

- `data/search_contract.json` (widened additively)
- `scripts/validate.py` (mapping gate reads raw snapshots too; message names both sides)
- `scripts/update_trending.py` (`merge_measurement_aliases` in the existing-row path)
- `tests/test_measurement_attribution.py`, `tests/test_validate.py`,
  `tests/test_fixture_mapping.py` (the contracts-declare-the-same-key assertion)
- `ARCHITECTURE.md` §6 row for `scripts/update_trending.py` (role wording only;
  no new target/stage/job — the gate lands in the EXISTING mapping stage)

## Not covered

- Teaching the search-leg skills about the key — that is issue #885, its own change.
- Populating any real alias entries — none exist today; nothing is invented (rule 3).
- Changing the attribution REFUSAL logic itself — #651's joint-figure rule stays
  byte-identical.
