# Tasks: engine-min-est-visibility-1129

- [x] `model_level_declared_engine_estimates()` helper in `scripts/validate.py` — reads model-level `engine_min_version` `(est)` values by name; verified by the new scenario
- [x] `check_model_footprint_copy` names each declared-estimate engine build report-only (emitted before its early return; no new stage/wiring) — verified by the new scenario
- [x] `tests/test_model_footprint_copy.py` scenario green on new code (20 passed) and RED on `origin/master`'s `validate.py` (helper absent, value unnamed)
- [x] OpenSpec change (proposal, spec with per-scenario test, tasks) created
- [x] `make lint`, `make architecture-check` (refresh if stale), `make openspec-check`, `make findings-check`, `make pr-message-check` green on the head
- [x] `OPENSPEC.md` index regenerated; PR opened with the five-section body and `closes #1129`
