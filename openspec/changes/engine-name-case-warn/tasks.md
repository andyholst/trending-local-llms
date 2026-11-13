# Tasks: engine-name-case-warn

- [x] `_engine_case_slips()` helper + guarded registry load in `scripts/update_trending.py` — verified by the new suite
- [x] `write_raw_snapshot` prints one `[write-raw] WARN:` per case slip, without renaming or refusing, independent of `verify_hf` — verified by the new suite
- [x] `tests/test_ingest_hf_verify.py::test_write_raw_warns_on_engine_name_case_slip` green on the new code and RED on the pre-change writer (ran the suite against the committed `scripts/update_trending.py`: 1 FAIL, the WARN checks)
- [x] AGENTS.md §8 guard row added
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [x] Local gates green (`make lint`, the write-raw suites, secret-scan, `make openspec-check`)
- [x] PR opened with the five-section body and `closes #645` (auto-merge then gates `validate` + `live-smoke` green on the head commit)
