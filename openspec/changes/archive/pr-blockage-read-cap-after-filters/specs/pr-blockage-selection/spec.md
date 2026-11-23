## ADDED Requirements

### Requirement: The PR-blockage read cap bounds log reads, not relevance

`pr_triggered_failures` SHALL apply the cheap filters — `conclusion in BAD_CONCLUSIONS`,
`headBranch in open_pr_branches(repo)`, and `createdAt >= now - window_hours` — BEFORE it calls
`bound_pr_block_runs()`, so that at most `PR_BLOCK_MAX_LOG_READS` LOG READS are spent per sweep and
every run whose log is fetched is concluded-bad, on a branch that is still an OPEN pull request,
and inside the window. `bound_pr_block_runs()` keeps its existing contract unchanged: it returns
the newest `cap` entries of the list it is given and the exact count it left.

#### Scenario: Newer green runs cannot crowd out a red open-PR run

- **Given** a newest-first `pull_request` run page holding `PR_BLOCK_MAX_LOG_READS` GREEN runs ahead of two red runs on two different open branches
- **When** the PR-blockage pass collects its runs
- **Then** the green runs are discarded by the pre-filter, both red runs are inside the read set, and their shared shape is grouped as blocking two open PRs
- **Test:** tests/test_pipeline_failure_issue.py::test_the_read_cap_is_spent_after_the_red_open_pr_filter

#### Scenario: A merged branch still never counts

- **Given** a red run whose head branch is no longer an open PR
- **When** the candidates are selected
- **Then** it is dropped before the cap, so it neither spends a log read nor counts toward `PR_BLOCK_MIN_PRS`
- **Test:** tests/test_pipeline_failure_issue.py::test_group_pr_blockages_needs_two_open_prs_and_drops_closed_branches

#### Scenario: The skipped count means red open-PR runs left over

- **Given** more candidate runs than `PR_BLOCK_MAX_LOG_READS`
- **When** the sweep reports its budget line
- **Then** the announced skipped count is the number of candidate runs beyond the cap, and the line still names the budget
- **Test:** tests/test_pipeline_failure_issue.py::test_pr_blockage_log_read_budget_is_bounded_and_announced

### Requirement: The open-PR branch set is read once per sweep

`record_pr_blockages` SHALL compute `open_pr_branches(repo)` once and pass the same set into the
collection pass, so adding the pre-filter costs no extra `gh pr list` call.

#### Scenario: One `pr list` read for the whole PR-blockage pass

- **Given** a sweep over several main pipelines
- **When** `record_pr_blockages` runs
- **Then** `open_pr_branches` is called exactly once and the collection pass receives that set
- **Test:** tests/test_pipeline_failure_issue.py::test_the_open_pr_branch_set_is_read_once_and_passed_down
