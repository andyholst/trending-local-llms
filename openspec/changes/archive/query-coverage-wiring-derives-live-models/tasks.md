# Tasks: query-coverage-wiring-derives-live-models

- [x] Replace the two pinned-literal wiring checks in
      `tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired` with
      store-derived expectations plus a non-vacuity check — verified:
      `python3 tests/test_query_coverage.py` PASSED 82 | FAILED 0 on the current store
- [x] Prove the old code was red and the guard still bites: the pinned literal is absent
      from the current `make -n _search-amd` expansion (byte-checked), matching the red CI
      runs 43775050919 / 43777818475; the synthetic uncovered-store test
      `test_an_uncovered_trending_model_fails_the_run` stays green in the same run
- [x] Spec scenarios each carry a `Test:` line naming a real test — verified:
      `make openspec-check` green on this branch
