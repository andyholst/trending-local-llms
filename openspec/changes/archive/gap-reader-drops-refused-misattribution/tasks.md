# Tasks: gap-reader-drops-refused-misattribution (#1007)

- [x] `captured_text` skips raw sources the ledger refused for the resolved
      store id (scan path) — verified: planted guard test green, and
      `80k context` no longer in the real bucket for `qwen-3.6-27b`
- [x] `_join_measurement_identity` skips refused (model, post) pairs (join
      bypass closed) — verified: planted join-bypass assertion green; real-store
      `unstructured:context_tokens` measured `["qwen-3.6-27b"] -> []`
- [x] `analyse` / `stated_untraceable` read the ledger by default through
      `load_refusals()` (rule 6d) — verified: planted `G.REFUSALS` fixture
      drives `analyse`'s own default load in the guard test
- [x] `MISATTRIBUTION_STAGE` pinned to `update_trending.REFUSAL_STAGES`;
      `_norm_citation` is the ONE pairing spelling — verified:
      `test_the_gap_reader_refusal_stage_is_the_seams_own_spelling` green
- [x] Real-store allowlists updated with MEASURED values (rule 6b/6c) —
      verified: full `tests/test_data_gap_analysis.py` suite green (312 tests)
- [x] Guard proven RED on the old code (`git show origin/master:...`) —
      verified: scratch staging against origin/master's scripts goes red on the
      #1007 assertions
- [x] OpenSpec change proposal + spec + tasks written; `make openspec-check`
      green — verified against this change's directory
