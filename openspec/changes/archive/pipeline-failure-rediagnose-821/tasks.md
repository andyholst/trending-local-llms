# Tasks: pipeline-failure-rediagnose-821

- [x] Read run 41860616772's alarm-job log (`gh api repos/.../actions/jobs/126681146852/logs`) and extract the bounded error block + target: `sweep-alarm`, the in-flight verdict line, `make: *** [Makefile:1333: sweep-alarm] Error 1`, exit 2
- [x] Raise the ledger row append-only (`error_excerpt`, `targets`, `fix_pr: 806`, `guard`, `rediagnosed_utc`, `rediagnosis_note`; `undiagnosed` kept) — `git diff` shows only added keys and grown values
- [x] Extend `tests/test_pipeline_failure_guard.py` with the row assertions + the post-merge gate shape — `python3 tests/test_pipeline_failure_guard.py` reports PASSED 39 | FAILED 0 (both #820 and #821 row tests)
- [x] `make pipeline-failure-guard-check` green on the raised ledger (exit 0)
- [x] `make lint` green; `make findings-check` green; `make secret-scan` clean
- [x] Suite subset green — `test_pipeline_failure_guard.py`, `test_sweep_alarm.py`, `test_pipeline_failure_issue.py`, `test_openspec_index.py`, `test_architecture.py`
- [x] `make openspec-check` green with all boxes ticked (runs the full active-change validation incl. this one)
- [x] PR opened (closes #821); change recorded+archived at head via `make openspec-record-pr` (its own commit on this branch)
