# refresh-aggregate-timeout

## ADDED Requirements

### Requirement: The refresh aggregate job has enough wall-clock time to finish validation

The `aggregate` job of the shipped `.github/workflows/refresh-bot.yml` SHALL declare a
job-level `timeout-minutes: 60`, matching the `search` job that feeds it, so a run whose
searches and validation are green is not cancelled in `Commit + open PR`. The shipped
workflow file SHALL be the artifact under test: a guard in the existing workflow-guard
test module SHALL read that file and fail whenever the aggregate job's job-level timeout
is not exactly `60` — in particular it SHALL go RED against the pre-change `30`. The
workflow's schedule, every other job timeout and all data/README/schema files SHALL be
unchanged by this requirement.

#### Scenario: a full aggregate pass is no longer cut off at 30 minutes

- **Given** the shipped `.github/workflows/refresh-bot.yml` whose aggregate job was cancelled at exactly 30 minutes while in `Commit + open PR` (run 46044870416)
- **When** the workflow-guard test module runs against that shipped YAML
- **Then** the aggregate job's job-level `timeout-minutes` parses as exactly `60`, while the same guard run against the base file reports `['30']` and fails
- **Test:** tests/test_workflow_guards.py::test_the_refresh_aggregate_timeout_allows_validation
