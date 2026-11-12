# Tasks: write-raw-verifies-links

- [x] `url_resolves()` helper in `scripts/update_trending.py` (404/410 dead, 403/429/5xx/transport indeterminate, per-write cache) — verified by the new suite
- [x] `write_raw_snapshot(verify_hf=True)` refuses a dead `source_post` measurement and strips a dead `engine_repo`, each with one loud `[write-raw] WARN:` — verified by the new suite
- [x] `tests/test_write_raw_link_verify.py` green on the new code and RED on the pre-change writer (ran it against `origin/master`'s `scripts/` snapshot: 5 FAIL)
- [x] AGENTS.md §8 guard row added
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [x] Full local gate run green (`make lint`, the write-raw suites in the container image, secret-scan, `make openspec-check`)
- [x] PR opened with the five-section body and `closes #644` (auto-merge then gates `validate` + `live-smoke` green on the head commit)
