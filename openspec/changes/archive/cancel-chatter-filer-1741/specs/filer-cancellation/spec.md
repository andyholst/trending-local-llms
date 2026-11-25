## ADDED Requirements

### Requirement: A cancelled push run with only cancellation chatter is not filed

`_superseded_cancelled_push` SHALL skip a run whose event is `push` and conclusion is
`cancelled` when its extracted block names no `make` target and every meaningful line
of that block is GitHub's own cancellation marker (`The operation was canceled.`),
after timestamps and `##[error]` decoration are stripped. The skip SHALL be announced
by the existing `skip N cancelled push-to-master run(s)` line and SHALL NOT append a
ledger row or file an issue for that run.

#### Scenario: the measured cancellation-marker shape is skipped

- **Given** a CANCELLED `push`-to-`master` run whose readable log region holds only
  `##[error]The operation was canceled.` (the shape of runs `45556943490` and
  `45596951334`) and names no `make` target
- **When** `make pipeline-failure-issue` sweeps the window
- **Then** no issue is filed for that run, no ledger row is appended, and the sweep
  announces one skipped cancelled push-to-master run
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_with_only_cancel_chatter_is_not_filed

#### Scenario: a real diagnosis on a cancelled push run still files

- **Given** a CANCELLED `push`-to-`master` run whose log carries a real `FAIL:` line
  and `##[error]Process completed with exit code 1.` (the #1615 counterexample)
- **When** the sweep runs
- **Then** one issue is filed, the ledger row carries the real error excerpt and a
  non-empty failure class, and no superseded-skip announcement is printed
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_with_a_readable_diagnosis_still_files

#### Scenario: the unreadable-log shape stays skipped

- **Given** a CANCELLED `push`-to-`master` run whose log read failed (`EMPTY_SHAPE` on
  both axes), as in the #1669 scene
- **When** the sweep runs
- **Then** it is skipped and announced exactly as before
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_is_not_filed
