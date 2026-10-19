# Proposal: measurement-engine-min-version

Issue: #371

## Why

`engine_min_version` is a requirement dimension whose only correct home is the
**measurement**: a minimum engine build (or the flags a run needed) is a property
of the engine that produced a t/s figure, and one model measured on two engines
has two different builds. The search prompt asks for it (`Makefile` `DIM_ASK`)
and the agent writes it there.

Both contracts declare `engine_min_version` OPTIONAL on the **model** row only
(`data/model_contract.json`, `data/search_contract.json`), and the measurement
item is `additionalProperties: false` — so the per-measurement form was **refused
outright** and the figure dropped silently (rule 3b):

    FAIL: search nvidia-20261018-110049.json: Additional properties are not allowed
    ('engine_min_version' was unexpected) (at ['models', 0, 'engines', 1])

Measured on run 39124432576 (fix-bot, PR #365): every leg captured correctly and
one legitimate field turned `make validate-search` red, so the refresh PR could
not merge.

## What Changes

- **Both contracts declare optional `engine_min_version` on the measurement
  item**, alongside the other four per-run dimensions. Additive: it is never
  added to `required` (§3b/§6b), so old snapshots still validate and no existing
  key moves or changes type.
- **`update_trending.MEASUREMENT_DIMENSION_FIELDS` names it** — the ONE
  definition of the per-measurement optional dimensions, which
  `tests/test_fixture_mapping.py` already reads, so the new key is covered by the
  existing "survives when stated / never invented when not" assertions without a
  second list to drift.
- **Ingest carries it and coerces it to text**: `normalize_model` applies the
  same `coerce_additive` rule to the measurement dimensions it already applies to
  the model-level ones, so a bare number the agent wrote is stored as its string
  form instead of failing the schema. `merge_engines` already carries a
  measurement's extra keys onto the store row, so no merge path changes.
- **The regression is locked by a test that RUNS the real check**: the real
  `scripts/validate.py::check_search_contract` against the real
  `data/search_contract.json`, over a raw snapshot carrying a per-measurement
  `engine_min_version` — it goes red on the pre-change contract.
- **The prompt says where the field belongs**: `Makefile` `DIM_ASK` now names
  `storage_offload` and `engine_min_version` among the dimensions to record ON
  the measurement, not only on the model row.

## Impact

`data/search_contract.json`, `data/model_contract.json`,
`scripts/update_trending.py` (`MEASUREMENT_DIMENSION_FIELDS`, `normalize_model`),
`Makefile` (`DIM_ASK`), `tests/test_measurement_footprint.py`, the OpenSpec change
and the regenerated `OPENSPEC.md` index.

`data/models.json` and `README.md` are **untouched**: no per-measurement
`engine_min_version` has reached the store yet (the key was refused before it
could), so nothing is backfilled here and no rendered table changes.

`AGENTS.md` §4 lists the optional per-measurement footprint keys
(`weight_gb, context_tokens, system_ram_min, storage_offload`) and now falls
behind the contracts by one key. That edit is **review-required and not written
here** — `AGENTS.md` is a protected agent-instruction file and this run has no
approver to consent to the write (rule 3c). The exact sentence is spelled out in
`findings.md`, which is the working file this run can write.

No make target, stage, pipeline job, image or script is added or renamed, so
`ARCHITECTURE.md` is unchanged (rule 6h) — verified by `make architecture-check`.

## Not covered

- **The `AGENTS.md` §4 dimension list** (above): a protected-file write that
  needs a human approver, recorded in `findings.md`.
- **Backfilling the new key onto existing measurements.** No raw snapshot on
  master states a per-measurement build, so there is nothing to backfill; when a
  future search captures one, `merge_engines` carries it through unchanged.
- **Filing `engine_min_version` per measurement instead of per model.** The
  analysis still reports the dimension per MODEL (issue #368); that is a separate
  change with its own guard.
- **fix-bot's missing per-round time bound** — how this run's repair was lost
  (two hours inside round 1 of 3, then the job limit). It is a pipeline defect,
  not a contract one, and is filed as its own issue (#372) rather than folded in
  here (rule 6g).
