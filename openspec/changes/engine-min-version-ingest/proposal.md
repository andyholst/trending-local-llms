# Proposal: engine-min-version-ingest

Issue: #877

## Why

#876 widened the `engine_min_version` detector so `make data-gaps` can now SEE the
build sentences posts actually use — but the detection stops at the report. Measured
on `origin/master` c9e2786: `unstructured:engine_min_version` names **7 models**
whose captured text states a build (`BigMoeOnEdge on stock llama.cpp (untouched
upstream, submodule)`, `MLX 4-bit Swift 1.5 adapter`, …) while `data/models.json`
carries no structured value for them. `data/model_contract.json` and
`data/search_contract.json` ALREADY hold the per-measurement `engine_min_version`
key, and the `data-search` skill already asks for it (#371) — so the missing piece
is the INGEST half: `scripts/update_trending.py` merges engine/tps/hardware/quant
and throws the build sentence away as prose. A gap the pipeline can see but never
closes re-files itself every sweep.

## What Changes

- `scripts/update_trending.py` gains `fill_engine_min_version`: during
  `ingest_raw_snapshots`, every measurement entering the store (incoming AND the
  store rows it merges into) whose free text (`quant`/`hardware`) matches the ONE
  detector `data_gap_analysis._ENGINE_MIN_TEXT` gets `engine_min_version` filled
  with the matched phrase VERBATIM — the measurement's existing `source_post` is
  the citation, so the value is attributed to a real post, never invented.
- The fill is ADDITIVE (rule 3b): it only fills a missing key, never overwrites an
  existing value, never raises or shrinks any other field; a measurement with no
  build phrase gains NOTHING (the precision class from #458/#213 stays exact).
- The detector has exactly ONE implementation (rule 6d): `update_trending` imports
  `_ENGINE_MIN_TEXT` from `data_gap_analysis`; a second copy is refused by a test.
- The fill prints loudly (`[engine-build-fill] N measurement(s) gained
  engine_min_version from captured phrasing`), like `refuse_fabricated_engines`.

## Impact

- `scripts/update_trending.py` (new fill seam + its call in `ingest_raw_snapshots`)
- `tests/test_engine_min_version_ingest.py` (new: fill, precision, no-overwrite,
  detector-single-implementation, unstructured-shrink on a fixture store)
- `make data-gaps` after the next merge: `unstructured:engine_min_version` shrinks
  (the Done-when measurement; baseline 7 measured 2026-11-13 on c9e2786).

## Not covered

- The 52 `not_captured` models (acquisition gap — only new searches close them;
  the prompts already ask since #371).
- The 4 `untraceable` models (capture gap — no post behind the value; no ingest
  may invent one).
- Widening `_ENGINE_MIN_TEXT` itself (done by #876; this change consumes it).
