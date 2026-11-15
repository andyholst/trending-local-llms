# alarms

## ADDED Requirements

### Requirement: A re-diagnosed UNDIAGNOSED ledger row of a fixed error class carries its fix attribution before its issue closes

When a pipeline-run-failure issue's failure class is already fixed by a merged PR with a guard
test under `tests/`, the ledger row for that run MUST be raised — append-only (rule 3b) — with
the merged `fix_pr`, the `guard` test `make test` collects, and its `targets` GROWN to the
parseable `make` target; every existing key and value (including the original `undiagnosed`
field) MUST be KEPT. Closing the issue with `make pipeline-failure-guard-check` green then rests
on that row, not on prose (rule 6r).

#### Scenario: the sweep-alarm row for run 43109817750 carries its landed fix and guard

- **Given** the committed ledger row for run 43109817750 (queued-alarm, issue #832), filed
  UNDIAGNOSED and later re-diagnosed (issue #969) with `error_excerpt` quoting the measured
  in-flight verdict line and `targets` naming `sweep-alarm`
- **When** the row is raised with the fix attribution that its identical-class siblings
  (#820/#821/#822/#824/#829) already carry
- **Then** it names `targets` GROWN to include `sweep-alarm`, `fix_pr: 806`, and
  `guard: "tests/test_sweep_alarm.py"` — a module `G.guard_test_exists` accepts — while the
  original `undiagnosed` field remains present and every prior value is unchanged
- **Test:** tests/test_pipeline_failure_guard.py::test_run_43109817750_is_rediagnosed_onto_the_landed_sweep_alarm_fix

#### Scenario: the closed issue passes the ledger gate on the exact post-merge shape

- **Given** the committed ledger and issue #832 CLOSED (the state every qa-validate push sees
  after this change merges)
- **When** `scripts/pipeline_failure_guard_check.py` verdicts the ledger
- **Then** the gate exits 0 — a CLOSED marker issue whose row names a real fix PR and a guard
  test on disk is a guarded close, not a laundering (rule 6r)
- **Test:** tests/test_pipeline_failure_guard.py::test_run_43109817750_is_rediagnosed_onto_the_landed_sweep_alarm_fix
