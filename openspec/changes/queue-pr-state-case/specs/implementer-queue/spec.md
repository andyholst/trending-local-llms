## ADDED Requirements

### Requirement: The queue tests a PR's open state case-insensitively

`issue_queue` SHALL treat a pull request as open when its `state` equals `open` in ANY letter case, because `gh pr list --json state` answers GitHub's API spelling `OPEN`. The comparison SHALL live in ONE helper used by both the branch path and the closing-PR path.

#### Scenario: gh's real `OPEN` spelling marks the issue implemented

- **Given** an open PR whose `state` is the literal `OPEN` and whose body closes #1176
- **When** `make issue-queue` builds the queue
- **Then** #1176 has an implementer and is not offered as `next-sweep`
- **Test:** tests/test_issue_queue_predicate.py::test_a_fix_prefixed_closing_pr_is_an_implementer

#### Scenario: The pre-existing branch path is repaired too

- **Given** a PR whose `state` is `OPEN` on the issue's `ci/data-gap-…` branch
- **When** the queue builds
- **Then** that issue still has an implementer
- **Test:** tests/test_issue_queue_predicate.py::test_a_fix_prefixed_closing_pr_is_an_implementer

#### Scenario: A closed PR does not mark an implementer

- **Given** a PR whose `state` is `CLOSED` and whose body closes #1176
- **When** the queue builds
- **Then** #1176 is still offered
- **Test:** tests/test_issue_queue_predicate.py::test_a_closed_closing_pr_does_not_mark_implementer

### Requirement: The guard plants gh's real state spelling

The guard SHALL feed the queue a PR payload whose `state` is `OPEN`, never a lowercase-only fixture, and SHALL pin that the PR-state test is one case-insensitive helper.

#### Scenario: A lowercase-only fixture is refused

- **Given** the guard's planted payload carrying `state: "OPEN"`
- **When** a case-sensitive implementation runs
- **Then** the check FAILS naming the state comparison
- **Test:** tests/test_issue_queue_predicate.py::test_the_queue_plants_ghs_real_open_spelling
