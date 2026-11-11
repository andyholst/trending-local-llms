# bot-coordination

## ADDED Requirements

### Requirement: The sweep reads every actionable label as one queue

The implementer's queue MUST contain the OPEN issues carrying ANY of `QUEUE_LABELS`
(`data-gap-analysis`, `tech-debt`), deduped by issue number and ordered oldest first, and a run
MUST take exactly ONE of them.

#### Scenario: two labels, one order

- **Given** one open issue labelled `data-gap-analysis` and one labelled `tech-debt`
- **When** `make issue-queue` runs
- **Then** both labels are queried, each issue appears once, and exactly one issue is `position=0`
- **Test:** tests/test_issue_review.py::test_the_queue_reads_both_labels_as_one_oldest_first_list

### Requirement: The verdict is judged against the fetched base

Before choosing a verdict the implementer MUST re-check the issue against the checkout it has
fetched (`make base-check` proves it IS `origin/master`), and an `EVIDENCE:` block that names no
checkable path or command MUST be refused, so a stale issue is closed on proof and a live one is
never closed on prose.

#### Scenario: an issue the base already fixed

- **Given** an issue whose defect is gone on the base, and a `close` verdict with `EVIDENCE`
  naming a tree path
- **When** the verdict is applied
- **Then** the issue is closed and labelled `agent:closed`
- **Test:** tests/test_issue_triage.py::test_three_mock_issues_decide_implement_refine_or_close_against_the_tree

#### Scenario: a live issue with a `close` verdict and prose evidence

- **Given** `TRIAGE: close` with `EVIDENCE: it is old and probably fixed`
- **When** the verdict is applied
- **Then** it is REFUSED and the issue is not closed
- **Test:** tests/test_issue_triage.py::test_three_mock_issues_decide_implement_refine_or_close_against_the_tree

#### Scenario: an issue that still holds

- **Given** a verdict of `TRIAGE: implement`
- **When** it is applied
- **Then** nothing is closed, labelled or commented — the run goes on to implement
- **Test:** tests/test_issue_triage.py::test_three_mock_issues_decide_implement_refine_or_close_against_the_tree
