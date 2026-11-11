# Proposal: measurement-store-split

Issue: #689 — `arch(data): normalize per-engine measurement store out of the model catalog`

Design: #692.

## Why

`data/models.json` is the single source of truth, and also a single **monolith**: the
inline `engines[]` array stores every per-engine (engine, hardware, quant, t/s, date,
source_post, footprint) measurement row inside each model object, restating the same
source post's engagement (likes/comments/views/reshares/interactions) on EVERY row it
appears on. A corrected or lost figure therefore drifts across N copies (#463/#525), the
same engagement contradicts across copies (#615), and a refresh hand-mutates one giant
file (#301).

The fix is a **normalised store**: measurement rows in one addressable place, engagement
published once per source post and referenced (not copied), and the catalog left as a
compact model reference — the flattened view staying byte-identical to the old inline
view (#463/#525 regression guard).

**This is the additive slice.** Per the owner's working default (#690), the refactor lands
staged and **never as a breaking change**: the new data pattern and its guards ship
ALONGSIDE the old flat store, every existing reader keeps reading `data/models.json` as
it always did, the old tests stay in CI, and only later slices switch readers to the
normalised store and delete the now-unused inline path.

## What Changes

- **`update_trending.split_store(store)`** — the ONE definition of the normalised split:
  returns `(catalog, measurements, posts)` where the catalog is the current model rows
  (no inline `engines[]`), `measurements` is keyed by `model_id` (rows of
  `{engine, tps, hardware, quant, date, source_post, [footprint…]}`, engagement counters
  stripped off the row), and `posts` is keyed by `source_post` URL ->
  `{date, likes, comments, reshares, views, interactions}` — engagement published once,
  stored as the MAX across referencing rows so a counter can never shrink (AGENTS §2.3b).
- **`update_trending.flatten_store(catalog, measurements, posts)`** — its inverse: rebuilds
  the exact pre-split flat store, splicing each measurement row's counters back from
  posts.json. A row whose source_post has no post entry resolves engagement to 0 (never a
  penalty).
- **`update_trending._measurement_identity(e)`** — the lossless-identity key for one
  measurement row (engine, tps, hardware, quant, date, source_post, footprint), excluding
  counters (which may only grow).
- **`update_trending.main()`** — when it writes the flat store, ALSO writes
  `data/measurements.json` + `data/posts.json` from `split_store(store)`. `data/models.json`
  itself is byte-unchanged; the two new files are an additive projection a reader may use
  now, and the source the switch-over slice will consume.
- **`data/measurements_contract.json` + `data/posts_contract.json`** — JSON Schema (draft
  2020-12) for the two new files, `additionalProperties: false`, mirroring
  `model_contract.json` conventions.
- **`validate.py` — three new checks** (`schema` stage): `check_measurements_contract`,
  `check_posts_contract` (the two new files conform to their contracts), and
  `check_split_flatten` (the shipped split files equal `split_store(models.json)` and
  `flatten_store` of them rebuilds every (model, engine, tps, source_post, footprint) row
  with no counter ever shrinking — the flatten-equality guard behind the #463/#525 loss
  class). Each skips cleanly when the split files are absent, so legacy stores and the
  temp-dir make tests are unaffected.
- **`tests/test_split_store.py`** — NEW test module (added to CI): the split pulls
  counters off rows, flatten reconstructs every identity tuple + counters, a missing post
  resolves to 0, posts hold the MAX across referencing rows, the two contracts validate
  the shipped split files, `check_split_flatten` passes on the real store, and the shipped
  split files match `split_store(models.json)`.
- **Shipped data** — `data/measurements.json` + `data/posts.json` generated from the
  current flat store, verified lossless.

## Impact

`scripts/update_trending.py`, `scripts/validate.py`, `tests/test_make_commands.py`
(2 lines: the fixture copies the new contracts), a new `tests/test_split_store.py`, five
new data/contract files, this OpenSpec change and the regenerated `OPENSPEC.md`. No new
make target, stage, job or image — `ARCHITECTURE.md` and `README.md` are unchanged
(rule 6h; `README.md` renders from the flat store, which the split does not touch).

## Not covered

- **Switching readers to the normalised store.** The renderer, sort, ingest and validate
  keep reading the flat `data/models.json`. Turning them onto `flatten(catalog,
  measurements, posts)` at load and writing `models.json` as the catalog is a LATER slice
  (owner working default #690: new code first, old code removed only once nothing reads it).
- **Removing the inline `engines[]` path** — a later slice, after readers move.
- **A live data migration / timer** — none (the fleet has no timers).
