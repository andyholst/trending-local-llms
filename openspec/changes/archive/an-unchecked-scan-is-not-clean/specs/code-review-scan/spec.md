# code-review-scan

## ADDED Requirements

### Requirement: an unchecked scan is never reported as clean

When a `code-review-scan` check could not run, the scan SHALL name the check that did not run in
its own output AND exit non-zero, so "checked and clean" and "could not check" can never be
mistaken for each other. A scan that asks for the API checks and is refused SHALL fail;
`--static-only` SHALL NOT fail, because it does not ask for them at all.

#### Scenario: a refused runs read fails the scan

- **GIVEN** a `gh` that refuses the workflow/run-count reads, so `check_workflow_never_ran`
  cannot run
- **WHEN** `code-review-scan` runs
- **THEN** it exits non-zero, names the check that did not run, and states that `no findings` is
  not a clean bill of health for it

- **Test:** `tests/test_code_review.py::test_a_scan_that_could_not_run_a_check_is_not_a_clean_scan`

#### Scenario: a fully-run scan stays green

- **GIVEN** a `gh` that answers the workflow/run-count reads (the production shape)
- **WHEN** `code-review-scan` runs
- **THEN** it exits 0 and does not claim any unchecked check

- **Test:** `tests/test_code_review.py::test_a_scan_whose_checks_ran_is_clean`

#### Scenario: --static-only does not fail for checks it never asked for

- **GIVEN** a `gh` that refuses everything
- **WHEN** `code-review-scan --static-only` runs
- **THEN** it exits 0 and claims no unchecked check, because it did not request the API checks

- **Test:** `tests/test_code_review.py::test_a_static_only_scan_does_not_fail_for_checks_it_never_asked_for`
