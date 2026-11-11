# Proposal: weight-gb-cannot-belong

Issue: tech-debt — "A measurement's weight_gb can belong to another model (Bonsai 2 9B
carries ~493GB NVFP4)" (filed while implementing #572, the above-48-GB tier ladder).

## Why

`data/measurements.json` → `bonsai-2-9b`, measurement `MLX` 36 t/s on
`4x Apple M5 Ultra Mac Studio (512GB each, Thunderbolt RDMA)` carries
`weight_gb: "~493GB NVFP4"` — yet Bonsai 2 9B is a 2 GB ternary model whose own footprint is
`2.0GB (ternary)`. The post (Chahatusharma 2111173528838103533) is about a different,
~493 GB NVFP4 model (Muse Spark Open); its t/s landed on the Bonsai row.

`weights_gb()` (#614) already REFUSES a 'stated' value more than `WEIGHTS_CONTRADICTION_FACTOR`
(10x) away from the model's own footprint — but only when a *reader* asks, and it falls back
to the model-level figure. The stored measurement still carries `~493GB NVFP4`, so every other
reader of the field (the card ladder's `weights-only` rows, the above-48-GB ladder,
`vram_need`, `data_gap_analysis`, `check_source_post_readback`) still sees a fabricated-looking
figure on a store whose whole premise is traceability (AGENTS.md rule 2). The reader-side
refusal does not repair the data for the next consumer.

## What Changes

- **`scripts/update_trending.py`** gains `weight_gb_contradiction_reason` and
  `refuse_weight_gb_contradictions` (the model arg carries its own footprint; the reason is
  computed with the same `_gb_value`/`WEIGHTS_CONTRADICTION_FACTOR` rules `weights_gb()` uses,
  one implementation): a measurement whose stated `weight_gb` contradicts the model's own
  footprint by more than `WEIGHTS_CONTRADICTION_FACTOR` is REFUSED at ingest, loudly, naming the
  model, the measurement and the source post — the same seam as `refuse_fabricated_engines`
  (#458), `refuse_misattributed_measurements` (#468) and
  `refuse_cross_model_duplicate_measurements` (#702). A measurement with no `weight_gb`, or
  whose model has no own footprint, is kept (fail-open; never refuse what is not provable).
- **`scripts/validate.py`** gains `check_weight_gb_contradictions`, a report-only scan in the
  `data` stage that prints any store row whose stated measurement `weight_gb` contradicts its
  model's own footprint (the shipped row is corrected by this change, so the scan is clean
  after it lands; a regression is reported, never silent — the same pattern as the #459
  duplicate-run and #531 source-post-readback scans).
- **`data/models.json` / `data/measurements.json` / `data/posts.json`** corrected additively
  (rule 3b): the `~493GB NVFP4` measurement, which cannot belong to a 2 GB ternary model, is
  removed from `bonsai-2-9b` (removal is a data correction this issue's evidence mandates — the
  figure is a different model's). No other model's value changes. A newer snapshot records the
  corrected store so `check_no_value_loss` stays green against the newest snapshot.
- **Tests:** `tests/test_weight_gb_contradiction.py` (new) locks the refusal over the exact
  shipped row, the fail-open carve-outs, the ingest wiring and the report-only scan.

## Impact

`scripts/update_trending.py`, `scripts/validate.py`, `data/measurements.json`,
`data/models.json`, `data/posts.json`, `data/snapshots/*`, `README.md`,
`tests/test_weight_gb_contradiction.py`, this OpenSpec change and the regenerated `OPENSPEC.md`.
No new target, stage, workflow or image (`ARCHITECTURE.md` unchanged, rule 6h); the new scan is
registered under the existing `data` stage and reaches CI through `make validate` (rule 6d).

## Not covered

- **The Muse Spark Open figure is NOT moved onto `muse-spark-open`.** Its post and counts stay
  where the search captured them (the Bonsai row explicitly no longer carries them); a re-merge
  of the raw snapshot still refuses the measurement at ingest, so the wrong row stays clean and
  a real Muse measurement is a separate data-gathering act, never this change.
- **A stated footprint that merely contradicts `vram_tier`/card size but matches within 10x** is
  kept: the factor is `WEIGHTS_CONTRADICTION_FACTOR` (10), the same bound `weights_gb()` already
  drew, and tightening it is a separate decision.
- **The historical snapshots that still contain the Bonsai `~493GB` row are NOT rewritten**
  (AGENTS.md rule 3c / history is additive). Only the newest snapshot — the corrected store —
  is added, so the value-loss guard has a consistent newest reference.
