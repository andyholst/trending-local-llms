# Proposal: model-id-matches-the-contract

Issue: #464 (measured on PR #461)

## Why

The store contract pins the model id to `^[a-z0-9][a-z0-9.\-]*$`. A search leg wrote an id by
hand with an underscore — `qwen3.8-27b-mlx_srv` (the model named after its engine, `mlx-serve`) —
and it survived both funnels:

- `--write-raw` wrote it into `data/raw/metal-20261020-114330.json`, so `search_contract` failed;
- `normalize_model` only ever CONSTRUCTED an id (`setdefault("id", _slug(name))`), never checked
  a provided one, so it reached `data/models.json` (`models[42]`) and `model_contract` failed too.

PR #461 therefore went red on three schema failures that a single `_` caused, and only
`fix-bot` could repair it — the "repair the PR, not the class" loop. The id also splits a model
in two: every lookup (`resolve_model_mapping`, the merge, the README) is by id.

## What Changes

- **`contract_id(value)`** — the normaliser: lowercase, `_`/space → `-`, anything outside
  `[a-z0-9.-]` → `-`, repeated `-` collapsed, leading separators stripped; `""` when nothing
  legal is left, so a caller falls back to `_slug(name)`.
- **`ID_PATTERN`** — the contract's pattern in one constant, so the code and the schema agree.
- **`write_raw_snapshot` normalises `id`** — the raw snapshot is legal the moment the leg writes
  it, so `search_contract` never sees the bad value.
- **`normalize_model` normalises `id` at ingest** — a raw row written before this rule still
  cannot reach the store. An id that already matches is left byte-identical, and an EXISTING
  model never reaches `normalize_model` (ingest matches it by id first), so rule 3b holds: no
  stored key is renamed.
- **Tests** (`tests/test_search_budget.py`): the measured id, mixed case/space, an already-legal
  id untouched, a nothing-legal value falling back, the raw snapshot written legal, and the
  ingest path normalising while leaving a legal id byte-identical.

## Impact

`scripts/update_trending.py` (one helper + two call sites), `tests/test_search_budget.py`,
`OPENSPEC.md`, this change. No new target, stage, job or image.

## Not covered

- **The id pattern is declared twice** (`data/model_contract.json` and
  `data/search_contract.json`). This change makes the CODE read one constant, but the two
  contract files still spell the pattern separately — a drift there is a contract change, not an
  ingest one.
- **Already-invalid ids in an OLD raw snapshot** are normalised at ingest, but the file on disk
  keeps its old spelling; rewriting history is not what this change is for.
