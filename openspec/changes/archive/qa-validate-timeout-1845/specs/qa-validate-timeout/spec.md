## ADDED Requirements

### Requirement: The qa-validate validate job has enough headroom to finish

The shipped `qa-validate.yml` SHALL give the `validate` job a job-level
`timeout-minutes` of 45, so a deterministic suite that passes is reported green
instead of being cancelled at the 30-minute ceiling.

#### Scenario: The shipped validate job pins 45 minutes

- **Given** the shipped `.github/workflows/qa-validate.yml` on the change's head
- **When** the workflow-guard module reads the `validate` job block
- **Then** its job-level `timeout-minutes` is `45`, and the same assertion fails with the base value `30`
- **Test:** tests/test_workflow_guards.py::test_validate_job_timeout_is_45_minutes

### Requirement: Raising the ceiling does not change what CI checks

The timeout change SHALL be confined to the `validate` job's budget: every
workflow SHALL still pass the tree-wide guard scan, and qa-validate SHALL still
run `make lint`.

#### Scenario: Every workflow still passes the guard scan

- **Given** the shipped workflow tree after the timeout change
- **When** the real guard scanner runs over it
- **Then** no workflow escapes the scan and every workflow still names its guard job
- **Test:** tests/test_workflow_guards.py::test_the_real_tree_scans_green_and_covers_every_workflow

#### Scenario: qa-validate still runs the lint gate

- **Given** the shipped `qa-validate.yml` after the timeout change
- **When** the workflow-guard module checks its wiring
- **Then** it still contains `make lint` and fix_loop still runs lint as its first check
- **Test:** tests/test_workflow_guards.py::test_the_scan_is_wired_through_the_makefile_into_lint
