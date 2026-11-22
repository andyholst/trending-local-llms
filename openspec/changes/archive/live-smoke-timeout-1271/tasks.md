# Tasks: live-smoke-timeout-1271

- [x] `live-smoke` `timeout-minutes` raised to cover 29 queries x 90s x 2 attempts with margin — verified by the new guard
- [x] `tests/test_smoke_search.py::test_ci_live_smoke_timeout_covers_the_worst_case_query_set` green on the new timeout and RED on `timeout-minutes: 25`
- [~] AGENTS.md §8 guard row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); the full row text is recorded in findings.md as an owed-row finding
- [x] ARCHITECTURE.md §4 `live-smoke` row names the timeout contract — `make architecture-refresh` + `make architecture-check` green
- [x] OpenSpec change (proposal, spec, tasks) + index regenerated — `make openspec-index` wrote `1 active, 399 archived`
- [x] Local gates green: `make lint`, `make architecture-check`, `make findings-check`, `tests/test_smoke_search.py` (75 checks)
- [x] PR opened with the five-section body and `closes #1271`
