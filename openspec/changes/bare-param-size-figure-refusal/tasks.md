# Tasks — bare-param-size-figure-refusal (issue #1018)

## 1. The seam sees the bare size

- [x] `scripts/update_trending.py`: `_BARE_PARAM_SIZE_RE` (standalone size inside a
  quant/throughput phrase; lookbehind refuses the `B` of `A2B` / `LFM2.5-24B-A2B`)
- [x] `scripts/update_trending.py`: `bare_param_sizes_in_text()` — a size that is part of a
  family-named mention is NOT bare (the #468 proof already governs it; one verdict per defect)
- [x] `scripts/update_trending.py`: `bare_param_size_figure_reason()` — joint figure,
  bake-off cue, own-model-named post, own-size and `measurement_model_aliases` rescues
- [x] `misattributed_measurement_reason` asks it when no family-named mention exists, so
  the ingest refusal and the validator's report reach ONE implementation (rule 6d)

## 2. Blast radius measured against the shipped data

- [x] Dry-ran `refuse_misattributed_measurements` over every `data/raw/*.json` row with the
  shipped store: 5 refusals before the change, 7 after — the 2 new ones are exactly the
  `qwen3.6-27b` `70B` sentences in `metal-20261014-210435.json`, no other capture changed
- [x] No value removed from `data/models.json`, `data/raw/*.json` or `data/refusals.json`
  (rule 3b/3b additive-only)

## 3. Tests that fail on the old code

- [x] `tests/test_measurement_attribution.py`: the planted `at 70B Q4` and `70B dense`
  sentences refused; own-size, `A2B`-token, `256GB`/`1.58TB/s` and multi-model/bake-off
  texts kept; the single-figure comparison refused as JOINT
- [x] `tests/test_measurement_attribution.py`: the seam run against the REAL
  `data/raw/metal-20261014-210435.json` (no fixture) — 2 refusals, real status URLs, the
  row's other measurements untouched
- [x] `make test` green; `make lint`, `make validate-data`, `make openspec-check`,
  `make architecture-check`, `make secret-scan` green

## 4. Rulebook and inventory

- [x] `AGENTS.md` §8: the regression-guard row for this seam
- [x] `make architecture-refresh` regenerates the inventory block (a `scripts/` file changed)

## 5. Owner decision owed (not mine to make)

- [~] Rule 3b owner ruling on the shipped `qwen3.6-27b` `llama.cpp` figure at `70B Q4` — blocked: the owner decides (removing or re-homing a stored value is a human act; `measurement_model_aliases` on the row is the data key that records the exception)
