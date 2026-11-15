# alarms

## ADDED Requirements

### Requirement: Ledger rows of an already-fixed error class are re-diagnosed onto the landed fix PR and its guard test

When a pipeline-run-failure issue's error class has already been fixed and guarded by a merged
change, every UNDIAGNOSED ledger row of that class MUST be raised — append-only — to name that
merged `fix_pr` and a `guard` test that exists under `tests/`, quoting the run log's own bounded
error block in `error_excerpt` and the `make` target the log names in `targets`; the original
`undiagnosed` field MUST be KEPT (rule 3b). The sibling issues then become closeable on ledger
proof rather than prose, and `make pipeline-failure-guard-check` stays green when they close
(rule 6r).

#### Scenario: both same-class sweep-alarm rows name the landed fix and guard

- **Given** the committed ledger rows for runs 41956933757 (issue #824) and 43049550731
  (issue #829), filed UNDIAGNOSED by the pre-#923 log reader
- **When** the rows are raised from their runs' own job logs
- **Then** each names `targets: ["sweep-alarm"]`, an `error_excerpt` quoting the measured
  in-flight verdict line, `fix_pr: 806`, and `guard: "tests/test_sweep_alarm.py"` — a module
  `G.guard_test_exists` accepts — while the original `undiagnosed` field remains present
- **Test:** tests/test_pipeline_failure_guard.py::test_run_41956933757_and_43049550731_are_rediagnosed_onto_the_landed_sweep_alarm_fix

#### Scenario: the sibling issues closed on those rows pass the ledger gate

- **Given** the committed ledger with issues #824 and #829 CLOSED (the state the sweep's
  already-fixed verdict produces after this change merges)
- **When** `scripts/pipeline_failure_guard_check.py` verdicts the ledger
- **Then** the gate exits 0 — closed rows that name a real fix PR and a guard test on disk are
  guarded closes, not launderings
- **Test:** tests/test_pipeline_failure_guard.py::test_run_41956933757_and_43049550731_are_rediagnosed_onto_the_landed_sweep_alarm_fix
