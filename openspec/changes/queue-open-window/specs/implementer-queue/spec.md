## ADDED Requirements

### Requirement: The queue reads only open pull requests

`issue_queue._pulls` SHALL request `--state open`, because `build` consumes no closed or
merged PR. A quiet open closing PR SHALL therefore never be crowded out of the result
window by more recently updated closed PRs.

#### Scenario: A quiet open closing PR survives a full window

- **Given** 150 `MERGED` PRs whose `updatedAt` is newer than a live open PR closing #1176
- **When** `_pulls` runs and `build` decides `has_implementer`
- **Then** the open PR is found and #1176 is not offered
- **Test:** tests/test_issue_queue_predicate.py::test_a_quiet_open_closing_pr_survives_a_full_window

#### Scenario: The request asks for open PRs only

- **Given** the recorded `gh` argv for `_pulls`
- **When** the guard inspects it
- **Then** it carries `--state open`
- **Test:** tests/test_issue_queue_predicate.py::test_the_pull_request_asks_for_open_prs_only

### Requirement: The guard fails on the pre-change window

The guard SHALL plant more closed PRs than the window holds, so a return to `--state all`
turns it red.

#### Scenario: `--state all` goes red

- **Given** the base seam (`--state all`)
- **When** the guard runs
- **Then** the open closing PR is absent from the window and the check FAILS
- **Test:** tests/test_issue_queue_predicate.py::test_a_quiet_open_closing_pr_survives_a_full_window
