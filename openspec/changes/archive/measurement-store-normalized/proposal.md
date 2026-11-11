# Proposal: measurement-store-normalized

Issue: #697 — `#689 slice 2: switch readers onto normalized measurement store, drop inline engines[]`
Design: #692. Parent: #682.

## Why

Slice 1 (#694) already ships the normalised store as an **additive projection**: every
store write emits `data/measurements.json` + `data/posts.json`, and the flatten-equality
guard proves they reconstruct the old inline `data/models.json`. What those two files
have not yet changed are the *readers*: `data/models.json` is still the flat monolith
(each model object inlines its `engines[]` rows, engagement restated on every row it
appears on, ~60% of the 714 KB file), and the renderer/sort/ingest/validate all consume
that inline shape directly.

**This is the switch-over slice.** The readers turn onto the normalised store —
`flatten(catalog, measurements, posts)` becomes the load path every reader materialises
from, and `data/models.json` is written as the compact catalog (no inline `engines[]`).
The old inline path is removed once nothing reads it, closing the #689 goal under the
full five-GWT acceptance criteria (the #463/#525/#411/#650 loss classes).

Per the owner's working default (#690) this lands as small, non-breaking deliveries and
never auto-merges a red PR; `data/snapshots/*.json` and the flat snapshot stay as the
flatten-equality oracle so no value is ever lost.

## What Changes

- **`update_trending.load_store()`** — the load seam: reads `data/models.json` (the
  catalog) + `data/measurements.json` + `data/posts.json` and returns
  `flatten_store(catalog, measurements, posts)` — the flat in-memory row shape every
  existing reader (render_readme, sort_models, ingest, validate) already operates on.
  If the split files are absent (legacy store / temp-dir fixture) it falls back to the
  flat store as-is.
- **`update_trending.main()`** — persists `data/models.json` as the **catalog** (output of
  `split_store`, no inline `engines[]`), alongside the already-written
  `data/measurements.json` + `data/posts.json`. The flat snapshot (`data/snapshots/*`)
  stays flat — it is the pre-switch oracle the flatten-equality guard compares against.
- **`data/model_contract.json`** — `engines` relaxed from required on a model row; the
  top-level `engines` registry (engine metadata) is unchanged.
- **`validate.py`** — `main()` loads through `load_store()` so every wired check keeps
  reading the same flat in-memory store; `check_split_flatten` (the #463/#525 guard) now
  proves the shipped split files == `split_store(load_store())` and that
  `flatten(measurements, posts)` matches the flat view, and `check_no_value_loss`/
  `check_no_removal` compare against the flat snapshots via the flattened store.
- **Engine support-surface (#338)** — the backends/measured-engine tables read the same
  `flatten(catalog, measurements, posts)` view, so nothing about backend derivation or
  supported-engine coverage changes.
- **`tests/test_measurements_split.py`** — NEW test module (added to CI) exercising the
  REAL business logic: (a) catalog rows carry no inline `engines`; (b) each measurement
  resolves engagement once from posts.json; (c) the flattened view equals the old inline
  view (guarded by `check_no_value_loss`); (d) the renderer materialises
  catalog × measurements with unchanged best-t/s ranking + footprint-aware card-fit; (e)
  the engine support-surface reads the same store. No logic mocks; only external-call
  mains are mocked and each has a real E2E companion.
- **`tests/test_split_store.py`** — updated so the flatten-equality fixture reads
  through the same split/flatten round-trip the writers now emit.
- **Shipped data** — `data/models.json` regenerated as the catalog from the current
  store; `data/measurements.json` + `data/posts.json` stay the canonical measurement +
  post stores. The rendered `README.md` is regenerated from the flattened view; its
  engagement-derived buzz/trend lines are **re-resolved from the canonical
  `data/posts.json`** (the intended GWT2 consequence), so a corrected post entry raises
  every referencing row — the README is re-resolved to the canonical value, not claimed
  byte-identical. (`tests/test_measurements_split.py::test_flatten_engagement_equals_posts_value_for_value`
  guards that every row's engagement equals `posts[source_post]` value-for-value.)

## Impact

`scripts/update_trending.py`, `scripts/validate.py`, `data/model_contract.json`, new
`tests/test_measurements_split.py`, `tests/test_split_store.py`, the new OpenSpec change
dirs + regenerated `OPENSPEC.md`, and regenerated `data/models.json`. Contract changes
are additive-relaxations only; no stage, make target, job or new image is introduced. The
`measurement-store-split` change dir is kept as-is.

## Not covered

- Removing `data/models.json`'s top-level `engines` registry or the flat snapshot mechanism.
- A live data migration or timer — none (the fleet has no timers).
- Dropping the `flatten_store`/`split_store` seam once the store is fully normalised — that
  is a post-switch cleanup; `flatten` remains the reader contract so the store's snapshots
  stay comparable.
