# Tasks: refusals-ledger-seen-count-idempotent

- [x] `record_ingest_refusals` keys a finding on (stage, model, engine, reason, source_post); a new finding appends one record with `seen_count: 1`, a repeat raises `seen_count` and stamps `last_seen_utc` and leaves `utc` untouched — verified by `tests/test_ingest_refusal_ledger.py::test_a_repeat_of_a_finding_grows_seen_count_instead_of_appending`
- [x] The repeat is announced in the log (`[ingest] refusals ledger: … repeat(s) counted …`) — verified by the same test's log check
- [x] A distinct stage/model/engine/reason/post is a separate finding and appends its own record — verified by `test_a_distinct_finding_still_appends_exactly_one_record`
- [x] `make validate` twice on an unchanged raw round changes only the counters (every finding field byte-identical, no appended record) — verified by `test_a_second_validation_pass_changes_only_the_counters`
- [x] `data_gap_analysis` carries `seen_count` and prints the refusal total as the sum of observations (rule 3b: never shrinks) — verified by `test_the_reported_total_counts_observations_never_copies`
- [x] The four new guards are RED on the pre-change scripts (ran the module against `origin/master`'s `scripts/update_trending.py` + `scripts/data_gap_analysis.py`: 5 FAIL then `KeyError: 'seen_count'`, rc=1 — the old writer has no counter at all)
- [x] AGENTS.md §8 guard row added
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + `make openspec-index`
- [x] Local gate run green (`make lint`, the refusal-ledger + gap-analysis suites, `make secret-scan`, `make openspec-check`, `make architecture-check`)
- [x] PR opened with the five-section body and one `closes #1148` (auto-merge then gates `validate` + `live-smoke` on the head commit)
