# Tasks

- [x] 1. The tracked change exists (this directory) before any edit
- [x] 2. `data/search_contract.json` declares optional `engine_min_version` on the measurement item (never `required`) and its engines item is still closed
- [x] 3. `data/model_contract.json` declares the same, so a stored per-measurement value validates
- [x] 4. `update_trending.MEASUREMENT_DIMENSION_FIELDS` names it, and `normalize_model` coerces the per-measurement dimensions to text (absent is never invented)
- [x] 5. `Makefile` `DIM_ASK` names `engine_min_version` and `storage_offload` among the dimensions to record ON the measurement
- [x] 6. `tests/test_measurement_footprint.py` proves the REAL `check_search_contract` accepts a per-measurement `engine_min_version`, and the guard was proved to go RED against the pre-change contract (both reverted: 4 FAIL, `Additional properties are not allowed ('engine_min_version' was unexpected)`; fixed: 32 passed, 0 failed)
- [x] 7. The existing guards still hold: `tests/test_fixture_mapping.py` (stated survives / absent never invented), `tests/test_hermes_prompts.py` (the ask names the measurement — two assertions added)
- [x] 8. `tests/test_engagement_contract.py` and `tests/test_data_gap_analysis.py` stay green — the contracts' optionality assertions still describe both files
- [x] 9. `data/models.json` and `README.md` are untouched (`git status --short` names neither)
- [x] 10. `findings.md` records the `AGENTS.md` §4 sentence this run cannot write (protected file) and the per-round-time-bound finding (#372); `make findings-check` green
- [x] 11. `OPENSPEC.md` regenerated; `make openspec-check`, `make architecture-check`, `make lint`, `make validate-search`, `make validate-mapped`, `make test` green
