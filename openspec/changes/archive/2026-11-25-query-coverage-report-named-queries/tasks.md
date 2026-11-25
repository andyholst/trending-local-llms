# Tasks: query-coverage-report-named-queries

- [x] Add the ONE filtered seam `_named_queries` and route `prompt_queries()` through it (same predicate, no behaviour change)
- [x] Compute `report()`'s derived/footprint/aged counts and `sent in total` from the filtered sets (curated base kept verbatim, only the derived half filtered)
- [x] Add the RED-first regression test `test_the_report_counts_only_queries_that_name_a_row`
- [x] Prove the test RED on the base revision (`git show origin/master:scripts/query_coverage.py`) and green here — base `PASSED 90 | FAILED 2` (`51` vs `43` sent, `2 + 2` vs `1 + 1`), head `PASSED 92 | FAILED 0`
- [x] Run the focused module, `make lint`; regenerate `OPENSPEC.md`
- [x] Write `findings/1693.md`, then record/archive against the PR
