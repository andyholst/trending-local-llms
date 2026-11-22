## ADDED Requirements

### Requirement: The PR-blockage pass has a bounded log-read budget

`pr_triggered_failures` SHALL read logs only from at most `PR_BLOCK_MAX_LOG_READS` runs and SHALL report the number of runs skipped beyond that cap.

#### Scenario: More red runs than the budget

- **Given** 20 concluded-bad `pull_request` runs inside the window
- **When** the PR-blockage pass collects failures
- **Then** at most the capped number of runs is read and the skipped count is carried to the sweep report
- **Test:** tests/test_pipeline_failure_issue.py::test_pr_blockage_log_read_budget_is_bounded_and_announced

### Requirement: The budget is announced

`record_pr_blockages` SHALL append a sweep line naming the cap and skipped count.

#### Scenario: Runs were skipped

- **Given** skipped runs were recorded
- **When** the sweep reports its result
- **Then** the line names both the cap and the number skipped
- **Test:** tests/test_pipeline_failure_issue.py::test_pr_blockage_log_read_budget_is_bounded_and_announced
