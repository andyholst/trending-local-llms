# Tasks

- [x] 1. `scripts/pipeline_failure_issue.py` — filer: main-pipeline run scan, job-log error block, scrubbed body, marker, per-job filing, UNDIAGNOSED path, exit-2 read failures
- [x] 2. `data/pipeline_failures.json` — append-only ledger seeded with the measured chain (run 43088760321 → issue #800 → PR #808 → guard test)
- [x] 3. `scripts/pipeline_failure_guard_check.py` — the closed-without-guard gate (ledger + marker-scan cross-check, exit 2 on unreadable ledger)
- [x] 4. `make pipeline-failure-issue`, `make pipeline-failure-guard-check`, `make pipeline-failure-ledger-pr-body` — internal recipes + public wrappers
- [x] 5. `queued-alarm.yml`: filer step after the three alarms; the SAME alarm job lands the ledger append as a reviewed PR through the Makefile (owner PAT, no closing keyword — a cross-job checkout would not carry the append)
- [x] 6. `qa-validate.yml`: `make pipeline-failure-guard-check` step in the `validate` job; `scripts/master_alarm.py` gate registry names it
- [x] 7. `scripts/bot_markers.py`: `pipeline-run-failure` registered with its writer
- [x] 8. `tests/test_pipeline_failure_issue.py` — real filer vs stub `gh`: filing, scrub, marker, dedup (ledger + closed marker), undiagnosed, exit 2, dry, ledger PR body, wiring
- [x] 9. `tests/test_pipeline_failure_guard.py` — real gate vs planted ledgers: every red shape, guarded close green (committed row), in-flight reports, exit-2 shapes, wiring
- [x] 10. `AGENTS.md` rule 6r + two §8 guard rows
- [x] 11. `ARCHITECTURE.md` §3 target rows, §4 queued-alarm + qa-validate steps, §6 script rows; `make architecture-refresh` + `make architecture-check` green (2026-11-12)
- [x] 12. `make lint` green; `make openspec-index` + `openspec-index-check` + `openspec-tasks-check` + the CLI `openspec validate --changes` green (the CLI seam ran locally against the pinned openspec image; the full `openspec-check` target runs in CI's validate job)
- [x] 13. `make test` in the test image: every module green except `test_check_openspec_tasks.py`, which was red only for THIS change's then-unticked boxes 11–13 (self-referential; they are ticked at the commit that opens the PR, and the suites it names — `test_bot_markers`, `test_master_alarm`, `test_workflows`, `test_makefile_only`, `test_secret_output`, `test_architecture`, both `test_pipeline_failure_*` — all passed)
