# Tasks: write-raw-snapshot-copy-payload

- [x] `write_raw_snapshot`'s model loop copies each model dict before rewriting it (`_m = dict(_m0)`) — verified: the write-raw suites green
- [x] The formats loop copies each format dict before rewriting it (`_f = dict(_f0)`) — verified: the new test went RED until this copy landed, then green
- [x] `tests/test_ingest_hf_verify.py::test_write_raw_never_mutates_the_caller_payload` green on the new code (34/0) and RED on the old `scripts/update_trending.py` (1 FAIL via `git stash`) — rule 6c proven
- [x] Regression run: `tests/test_write_raw_link_verify.py` (10/0) and `tests/test_search_budget.py` (54/0) unchanged
- [x] AGENTS.md §8 guard row added
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [x] Full local gate run green (`make lint`, secret-scan, `make openspec-check`)
- [x] PR opened with the five-section body and `closes #646` (auto-merge then gates `validate` + `live-smoke` green on the head commit)
