## ADDED Requirements

### Requirement: A failed-rebase announcement names the branch worktree as the invocation dir

`pr_health.rebase_comment_body` SHALL name the branch's own worktree as the directory from
which the following `make base-rebase BRANCH=<branch>` step must be run, because that seam
resolves its head from the invocation directory and a caller following the remedy from the
shared `master` checkout gets a silent `up-to-date` for a behind branch (#1330/#1335).

#### Scenario: The remedy comment tells the caller which checkout to use

- **Given** a behind `ci/` bot branch whose rebase git refused, announced on the PR thread
- **When** `rebase_comment_body` composes the marker-stamped announcement
- **Then** the comment includes `cd <worktree for <branch>>` beside the `make worktree-resume`
  and `make base-rebase` steps, and the announcement still carries exactly one marker
- **Test:** tests/test_pr_health.py::test_a_failed_rebase_round_announces_on_the_pr_thread_once
