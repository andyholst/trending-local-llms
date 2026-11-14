# alarms

## ADDED Requirements

### Requirement: An UNDIAGNOSED ledger row is re-diagnosed from the readable run log before its issue closes

When a pipeline-run-failure issue's job log becomes readable (the filer's log-reader defect
of issue #923 is fixed), the ledger row for that run MUST be raised — append-only — with the
log's own bounded error block (`error_excerpt`), the `make` target the log names
(`targets`), the merged fix PR for the diagnosed error class (`fix_pr`) and a guard test that
exists under `tests/` (`guard`); the original `undiagnosed` field MUST be KEPT (rule 3b).
Closing the issue with `make pipeline-failure-guard-check` green then rests on that row, not
on prose (rule 6r).

#### Scenario: the re-diagnosed sweep-alarm row carries its landed fix and guard

- **Given** the committed ledger row for run 41788683672 (queued-alarm, issue #820), filed
  UNDIAGNOSED because the log reader of the time refused escape sequences
- **When** the row is raised from the run's own job log
- **Then** it names `targets: ["sweep-alarm"]`, an `error_excerpt` quoting the measured
  in-flight verdict line, `fix_pr: 806`, and `guard: "tests/test_sweep_alarm.py"` — a module
  `G.guard_test_exists` accepts — while the original `undiagnosed` field remains present
- **Test:** tests/test_pipeline_failure_guard.py::test_run_41788683672_is_rediagnosed_with_its_landed_guard

#### Scenario: the closed issue passes the ledger gate on the exact post-merge shape

- **Given** the committed ledger and issue #820 CLOSED (the state every qa-validate push sees
  after this change merges)
- **When** `scripts/pipeline_failure_guard_check.py` verdicts the ledger
- **Then** the gate exits 0 — a CLOSED marker issue whose row names a real fix PR and a guard
  test on disk is a guarded close, not a laundering
- **Test:** tests/test_pipeline_failure_guard.py::test_run_41788683672_is_rediagnosed_with_its_landed_guard
