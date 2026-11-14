# Tasks: rediagnose-sweep-alarm-rows-976

- [x] Read both alarm-job logs (`gh api .../actions/jobs/127014006697/logs`, `.../130622645547/logs`) — both carry the identical in-flight verdict line + `make: *** [sweep-alarm] Error 1`
- [x] Raise both ledger rows append-only (`error_excerpt`, `targets`, `fix_pr: 806`, `guard`, `rediagnosed_utc`, `rediagnosis_note`; `undiagnosed` kept) — `git diff` shows only added keys and grown values
- [x] Extend `tests/test_pipeline_failure_guard.py` with the two-row assertions + the post-merge gate shape — the suite reports PASSED/FAILED with 0 failures
- [x] `make pipeline-failure-guard-check` green on the raised ledger (exit 0)
- [x] `make lint` green; `make findings-check` green; `make secret-scan` clean
- [x] Suite subset green — `test_pipeline_failure_guard.py`, `test_sweep_alarm.py`, `test_pipeline_failure_issue.py`, `test_openspec_index.py`, `test_architecture.py`
- [x] `make openspec-check` green with all boxes ticked
- [x] PR opened (closes #976); change recorded+archived at head via `make openspec-record-pr` (its own commit on this branch)
