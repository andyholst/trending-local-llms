# Tasks

- [x] 1. Write the proposal + GWT capability spec for issue #702 (`cross-model-ingest-refusal`: refuse at ingest a tuple already carried by a different model id, reuse the #695 allow-list).
- [x] 2. `scripts/update_trending.py`: `CROSS_MODEL_ALLOW_LIST` — the single-source allow-list moved verbatim from the #695 test (11 legitimate tuples), shared by the ingest refusal and the post-merge gate.
- [x] 3. `scripts/update_trending.py`: `_cross_model_identity()` — the exact `(engine, tps, hardware, source_post)` key the report-only `same_post_cross_model_duplicates` scan uses.
- [x] 4. `scripts/update_trending.py`: `cross_model_carriers(store)` — model ids that ALREADY carry each tuple (the established owner), so only a copy ARRIVING at ingest is refused.
- [x] 5. `scripts/update_trending.py`: `refuse_cross_model_duplicate_measurements(model, carriers)` — splits (kept, refused) by identity tuple vs the owner, honoring the allow-list, never refusing the established owner; wired into `ingest_raw_snapshots()` beside the fabricated (`refuse_fabricated_engines`) and misattribution (`refuse_misattributed_measurements`) seams.
- [x] 6. `tests/test_cross_model_attribution.py`: `ALLOW_LIST = ut.CROSS_MODEL_ALLOW_LIST` (single source; no copy-paste divergence) + module-level `import update_trending`.
- [x] 7. `tests/test_cross_model_attribution.py`: real-logic tests — carrier identity, established-owner kept, copy refused with owner named, allow-listed variant kept (`test_cross_model_carriers_are_the_store_already_merged`, `test_a_copy_onto_a_model_the_post_never_measured_is_refused`, `test_a_documented_allow_listed_pair_is_kept_at_ingest`).
- [x] 8. `tests/test_cross_model_attribution.py`: E2E — `test_ingest_refuses_a_re_capture_before_it_merges` runs the REAL `ingest_raw_snapshots` in a temp `TRENDING_DATA_DIR` and asserts a re-capture is refused while a legit measurement on the same row still merges.
- [x] 9. `tests/test_workflows.py` hygiene: every `test_*` in `test_cross_model_attribution.py` is called from `main()` (12/12, verified), `main()` returns non-zero on failure.
- [x] 10. Verified: `test_cross_model_attribution.py` 88 passed / 0 failed, `validate --only data,removal,schema` QA PASSED, all 12 tests named in the spec grep out of the test tree, `OPENSPEC.md` regenerated, `make openspec-check` green.
