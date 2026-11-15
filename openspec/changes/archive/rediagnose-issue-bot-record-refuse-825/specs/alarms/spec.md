# alarms

## ADDED Requirements

### Requirement: A record-pr refusal on an unbound change is closed on a re-diagnosed ledger row

An implementation run that died at `make openspec-record-pr` because its ACTIVE change carried no
`Issue:` binding MUST be tracked by the failure filer, and — the class being fixed and guarded by
the landed binding-check (`make openspec-binding-check`, `tests/test_openspec_binding.py`) — its
UNDIAGNOSED ledger row MUST be raised append-only naming that `fix_pr` and `guard`, quoting the
refusal block and growing `targets` only (never shrinking), so the tracked issue closes on ledger
proof and `make pipeline-failure-guard-check` stays green after the close (rule 6r).

#### Scenario: the issue-bot row names the landed binding fix

- **Given** the committed ledger row for run 42973469114 (issue #825), filed UNDIAGNOSED by the
  pre-#923 log reader
- **When** the row is raised from the run's own job log, which shows the refusal
  `[openspec-record-pr] REFUSED: no change — active or archived — references Issue: #527` followed
  by `make: *** [Makefile:347: openspec-record-pr] Error 2`
- **Then** the row names `fix_pr: 955` and `guard: "tests/test_openspec_binding.py"` — a module
  `G.guard_test_exists` accepts — quotes the refusal in `error_excerpt`, grows `targets` to
  `["openspec-record-pr"]`, and keeps the original `undiagnosed` field (rule 3b)
- **Test:** tests/test_pipeline_failure_guard.py::test_run_42973469114_is_rediagnosed_onto_the_landed_openspec_binding_fix

#### Scenario: the sibling issue closed on that row passes the ledger gate

- **Given** the committed ledger with issue #825 CLOSED beside its re-diagnosed siblings
- **When** `scripts/pipeline_failure_guard_check.py` verdicts the ledger
- **Then** the gate exits 0 — a closed row that names a real fix PR and a guard test on disk is a
  guarded close, not a laundering
- **Test:** tests/test_pipeline_failure_guard.py::test_run_42973469114_is_rediagnosed_onto_the_landed_openspec_binding_fix
