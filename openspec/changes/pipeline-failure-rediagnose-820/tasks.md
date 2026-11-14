# Tasks: pipeline-failure-rediagnose-820

- [x] Read run 41788683672's alarm-job log and extract the bounded error block + target (the log is readable after the #923 fix; `gh run view 41788683672 --log --job 126436727581` names `sweep-alarm` and the in-flight verdict line)
- [x] Raise the ledger row append-only (`error_excerpt`, `targets`, `fix_pr: 806`, `guard`, `rediagnosed_utc`, `rediagnosis_note`; `undiagnosed` kept) — `git diff` shows only added keys and grown lists
- [x] Extend `tests/test_pipeline_failure_guard.py` with the row assertions + the post-merge gate shape — `python3 tests/test_pipeline_failure_guard.py` reports PASSED 33 | FAILED 0
- [x] `make pipeline-failure-guard-check` green on the raised ledger (exit 0; "2 diagnosed failure(s) closed with a landed fix PR + guard test")
- [x] `make openspec-index` green with the change present ("3 active, 282 archived"); `make lint` green (workflow-guard-scan OK); `make findings-check` green (2 findings well-formed); `make secret-scan` clean
- [x] Suite subset green — every `tests/test_*.py` except the known host-only modules passed; the single failure was `test_check_openspec_tasks.py` refusing these unticked boxes, re-run green after this tick
- [x] `make openspec-check` green with all boxes ticked (runs the full active-change validation incl. this one)
- [x] PR opened (closes #820); change recorded+archived at head via `make openspec-record-pr` (its own commit on this branch)
