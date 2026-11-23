# pipeline-failure-ledger

## ADDED Requirements

### Requirement: The PR-blockage grace is derived from a stated, measured repair window

The filer SHALL define `PR_BLOCK_GRACE_HOURS` by assignment from a named
`PR_BLOCK_REPAIR_WINDOW_HOURS`, never as a bare literal. The constant's comment SHALL name the
measured failure that sets the window and SHALL refuse a cadence basis for a dispatch-only
sweep. The numeric grace SHALL remain the same as before the change so the guard's report/red
boundary does not move.

#### Scenario: the grace names its measured basis instead of a bare literal

- **Given** `scripts/pipeline_failure_issue.py` with a PR-blockage grace used by
  `make pipeline-failure-guard-check`
- **When** a reader inspects the definition of `PR_BLOCK_GRACE_HOURS`
- **Then** it is assigned from `PR_BLOCK_REPAIR_WINDOW_HOURS` (24 h), whose comment names the
  measured #1164 outage (runs 44651246625 / 44651246366) and states that no sweep cadence is
  owed because `queued-alarm.yml` is dispatch-only after #1029
- **Test:** tests/test_pipeline_failure_guard.py::test_the_pr_block_grace_is_derived_from_its_stated_repair_window

#### Scenario: a bare-literal grace is refused by the regression guard

- **Given** the pre-change file where `PR_BLOCK_GRACE_HOURS = 24` is a literal with no named
  repair window
- **When** `tests/test_pipeline_failure_guard.py` runs against it
- **Then** the derivation checks FAIL (a missing `PR_BLOCK_REPAIR_WINDOW_HOURS`, no assignment
  line, no measured-basis comment) and the module exits non-zero
- **Test:** tests/test_pipeline_failure_guard.py::test_the_pr_block_grace_is_derived_from_its_stated_repair_window

### Requirement: The guard reads the same derived seam as the filer

`scripts/pipeline_failure_guard_check.py` SHALL import the same `PR_BLOCK_GRACE_HOURS` from the
filer so the report/red boundary cannot drift from the documented repair window. The existing
time-based behaviour — a recorded PR-blocking row stays a report inside the grace and is RED
once it is past — SHALL be unchanged.

#### Scenario: the 24 h boundary still separates report from red

- **Given** a `pull_request`-triggered ledger row with no fix PR, filed 6 h and 30 h before the
  injected clock
- **When** `make pipeline-failure-guard-check` judges each row
- **Then** the 6 h row is a report (exit 0) and the 30 h row is RED (exit 1), naming the shape,
  the blocked PRs and the missing fix
- **Test:** tests/test_pipeline_failure_guard.py::test_a_recorded_pr_blockage_whose_fix_never_lands_is_red_after_its_grace
