# Tasks

- [x] 1. Write the proposal + `card-fit` capability spec for issue #572.
- [x] 2. `HIGH_TIERS_GB`, `HIGH_TIER_LABELS`, `total_memory_gb()`, `high_tier_fit()`, `high_tier_measurements()`, `high_tier_rows()` in `scripts/update_trending.py`.
- [x] 3. The need gate: a model is placed above 48 GB only when its weight footprint exceeds 48 GB (the first cut listed an 8B on a 64 GB Mac mini).
- [x] 4. `weights_gb()` refuses a footprint more than 10x the model's own (the Bonsai 2 9B / `~493GB NVFP4` row).
- [x] 5. README renders the four tiers with an anchor index entry, a named collection gap and the same `ran-on` / `weights-only` labels.
- [x] 6. `check_card_tables` validates both ladders with their own row function; above-48 coverage is report-only.
- [x] 7. `tests/test_card_fit.py`: 5 new tests (need gate, weights-only labelling, the contradiction, the render, a falsified row) — 96 passed, 0 failed.
- [x] 8. `README.md` and `data/models.json` regenerated from the shipped store (10 real rows above 48 GB).
- [x] 9. `make openspec-check`, `make architecture-check`, `make lint`, `make findings-check` green; the `AGENTS.md` §8 row is OWED (protected file) and named in the PR body.
