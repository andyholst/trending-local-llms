# Tasks: search-smoke-source-reachability

- [x] `scripts/smoke_search.py::main` collects per-leg outcomes and labels an all-missed leg QUERY-STARVED when another leg proved the mirror reachable — verified: the scripted full-run guard passes
- [x] `tests/test_smoke_search.py` guards the note and the full-outage block (72/0); the starved-leg guard is RED on the old script — rule 6c proven
- [x] AGENTS.md §8 row updated with the source-vs-query distinction
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [x] Full local gate run green (`make lint`, `make architecture-check`, `make findings-check`, `make openspec-check`; `make test` 145 modules once the task boxes are ticked — an earlier run was red only on `test_check_openspec_tasks.py` for these boxes)
- [x] PR #1225 head updated and its CI green — the blocked PRs #1206/#1212 then re-check automatically
