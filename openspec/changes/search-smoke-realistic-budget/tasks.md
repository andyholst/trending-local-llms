# Tasks: search-smoke-realistic-budget

- [x] `Makefile` owns `SEARCH_SMOKE_BUDGET ?= 90`; `_search-smoke` uses it and `search-smoke` forwards it — verified: the guard finds the pin and the recipe
- [x] `qa-validate.yml` and `refresh-bot.yml` pass the budget explicitly and name 90s in their step titles — verified: the guard reads both files
- [x] `tests/test_smoke_search.py::test_ci_search_smoke_budget_is_realistic` is green on the new tree (70/0) and RED on `origin/master`'s Makefile/workflows (missing pin) — rule 6c proven
- [x] AGENTS.md §8 guard row added for the budget pin and the red-on-old-code proof
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [x] Full local gate run green (`make test` 145/0 after the task boxes were ticked, `make lint`, `make architecture-check`, `make openspec-check`, `make findings-check`) — the one local `make test` before ticking was red only on `test_check_openspec_tasks.py` for these unticked boxes
- [x] PR opened with the five-section body and `closes #1224` (auto-merge requires `validate` + `live-smoke` green on the head)
