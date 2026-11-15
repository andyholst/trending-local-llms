# alarms

## ADDED Requirements

### Requirement: A cancelled delivery whose class is already guarded is closed on a re-diagnosed ledger row

A main-pipeline run that concluded `cancelled` while its own checks were green MUST be tracked by
the failure filer (`BAD_CONCLUSIONS` includes `cancelled`), and when the class is already fixed
and guarded by a merged change, its UNDIAGNOSED ledger row MUST be raised append-only — naming
the landed `fix_pr` and an existing `guard` test, quoting the log's bounded error block — so the
tracked issue closes on ledger proof and `make pipeline-failure-guard-check` stays green after
the close (rule 6r).

#### Scenario: the cancelled refresh-bot aggregate row names the landed guard

- **Given** the committed ledger row for run 41929086636 (issue #823), filed UNDIAGNOSED by the
  pre-#923 log reader
- **When** the row is raised from the run's own job log, which shows `PASSED 124 | FAILED 0`
  followed by `##[error]The operation was canceled.`
- **Then** the row names `fix_pr: 806` and `guard: "tests/test_sweep_alarm.py"` — a module
  `G.guard_test_exists` accepts — quotes both log lines in `error_excerpt`, keeps the original
  `undiagnosed` field and the justified empty `targets` (rule 3b)
- **Test:** tests/test_pipeline_failure_guard.py::test_run_41929086636_is_rediagnosed_onto_the_cancelled_delivery_guard

#### Scenario: the sibling issue closed on that row passes the ledger gate

- **Given** the committed ledger with issue #823 CLOSED beside its re-diagnosed siblings
  (#820, #821, #822, #824, #829, #800)
- **When** `scripts/pipeline_failure_guard_check.py` verdicts the ledger
- **Then** the gate exits 0 — a closed row that names a real fix PR and a guard test on disk is a
  guarded close, not a laundering
- **Test:** tests/test_pipeline_failure_guard.py::test_run_41929086636_is_rediagnosed_onto_the_cancelled_delivery_guard
