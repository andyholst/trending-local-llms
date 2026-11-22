## ADDED Requirements

### Requirement: The queue reads only open PRs

`scripts/issue_queue.py::_pulls` SHALL request only OPEN pull requests from `gh`, because
`build` counts an implementer only when a PR is open. Closed and merged PR bodies SHALL
NOT occupy the `--limit` window or cross the wire.

#### Scenario: A live closing PR survives a full window of closed PRs

- **Given** 100 CLOSED PRs updated more recently than one OPEN PR that closes a queued issue
- **When** `_pulls` reads the queue's PR list
- **Then** the OPEN PR is still returned and the closing binding is visible to `build`
- **Test:** tests/test_issue_queue_predicate.py::test_an_open_closing_pr_survives_a_window_of_closed_prs

### Requirement: The regression is proven against the executing seam

The guard SHALL drive the real `issue_queue._pulls` against a stubbed external `gh` and
FAIL on the pre-change `--state all` request, never on a stand-in for the product code.

#### Scenario: The pre-change request is RED

- **Given** the pre-change `_pulls` asking `gh pr list --state all --limit 100`
- **When** the test plants the 100-closed-plus-one-open fixture
- **Then** the OPEN PR is missing and the module reports `FAILED 1`
- **Test:** tests/test_issue_queue_predicate.py::test_an_open_closing_pr_survives_a_window_of_closed_prs
