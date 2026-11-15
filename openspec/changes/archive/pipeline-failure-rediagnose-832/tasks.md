# Tasks: pipeline-failure-rediagnose-832

- [x] Read run 43109817750's alarm-job error from the re-diagnosed ledger row (`data/pipeline_failures.json`) — the bounded block names `sweep-alarm` and the in-flight verdict line, the #801/#806 class
- [x] Raise the ledger row append-only (`fix_pr: 806`, `guard: tests/test_sweep_alarm.py`, `targets` grown to `sweep-alarm`, `rediagnosis_note` extended; `undiagnosed` and every prior value kept) — `git diff` shows only added keys and grown lists
- [x] Extend `tests/test_pipeline_failure_guard.py` with the row assertions + the post-merge gate shape — `python3 tests/test_pipeline_failure_guard.py` reports PASSED
- [x] `make pipeline-failure-guard-check` green on the raised ledger with issue #832 CLOSED (exit 0; guarded close, not a laundering)
- [x] `make openspec-index` green with the change present; `make findings-check` green (`findings.md` well-formed); `make lint` green (newline + wiring gates)
- [x] `make openspec-check` green (runs the active-change validation, the index-current check, the tasks gate, the spec-tests gate and the binding gate on this change)
- [x] PR opened (closes #832); change recorded+archived at head via `make openspec-record-pr` (its own commit on this branch)
