## ADDED Requirements

### Requirement: A closed pipeline-failure issue names its landed fix in the ledger

Every `data/pipeline_failures.json` entry whose issue is CLOSED names its landed fix PR and its guard test (`fix_pr` non-null, `guard` a `tests/test_*.py` module that exists in `tests/`), so `make pipeline-failure-guard-check` can prove the error class is locked rather than merely closed.

#### Scenario: The raised row clears the gate

Given the ledger entry for run 43110467252 (issue #833) naming `fix_pr: 1057` and `guard: "tests/test_implement_stream.py"`
When the gate's verdict runs over the committed ledger with issue #833 CLOSED
Then the entry reports guarded, the verdict exits 0, and the master push run clears the gate

- **Test:** tests/test_pipeline_failure_guard.py::test_run_43110467252_is_raised_onto_the_landed_implement_guard

#### Scenario: An unraised closed entry stays red

Given a planted ledger entry whose issue is CLOSED with `fix_pr: null`
When the gate's verdict runs over it
Then the verdict exits 1 naming the run and issue — the raise does not launder the error class away

- **Test:** tests/test_pipeline_failure_guard.py::test_closed_without_guard_is_red
