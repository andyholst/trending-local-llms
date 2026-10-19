# issue-queue

## ADDED Requirements

### Requirement: In-flight status comes from the start comment, never from a run title

The queue MUST treat an implementer as started only when the issue carries a fresh
start comment or fresh start activity, and MUST NOT attribute a run to an issue by
matching the issue number inside a run's `displayTitle`.

#### Scenario: a run's title mentions the issue but no start comment exists

- **Given** an in-progress `issue-bot` run whose `displayTitle` contains `#176`, and an issue with no start marker
- **When** the queue is built
- **Then** the issue is reported `started=0` and never `reason=run-in-flight`
- **Test:** tests/test_issue_review.py::test_the_queue_attributes_a_run_by_its_start_comment_not_its_title

#### Scenario: a fresh start comment still marks the issue started

- **Given** the same issue with a fresh `<!-- issue-bot-start: … -->` comment
- **When** the queue is built
- **Then** it is reported `started=1`
- **Test:** tests/test_issue_review.py::test_the_queue_attributes_a_run_by_its_start_comment_not_its_title

### Requirement: The queue does not read a field it cannot use

The queue MUST NOT call `gh run list` (the field it read could not identify an issue,
so the call bought nothing and cost a network round trip per build).

#### Scenario: the queue runs

- **Given** any set of candidates
- **When** the queue is built with the `gh` stub recording every call
- **Then** no `run list` invocation appears in the log
- **Test:** tests/test_issue_review.py::test_the_queue_attributes_a_run_by_its_start_comment_not_its_title
