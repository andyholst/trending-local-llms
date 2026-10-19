# issue-queue

## ADDED Requirements

### Requirement: A verdict hold is measured from the start of its chain

The queue MUST report how long the CURRENT verdict has been held, measured from the
oldest reviewer marker of the unbroken chain (consecutive markers less than
`VERDICT_TTL_HOURS` apart), and MUST report it on the row
(`verdict_held_since`, `verdict_held_hours`).

#### Scenario: a verdict re-dated every 20 h for 40 h

- **Given** an issue with a verdict label and reviewer markers 40 h, 20 h and 1 h old
- **When** the queue is built
- **Then** the row reports `verdict_held_hours=40`, `verdict_fresh=1` and the issue is still held
- **Test:** tests/test_issue_review.py::test_a_reviewer_that_keeps_re_dating_a_verdict_cannot_hold_for_ever

#### Scenario: a stale gap does not extend the hold

- **Given** reviewer markers 2 h and 300 h old
- **When** the chain start is computed
- **Then** it is the 2 h marker — the hold is the newest link, not the old one
- **Test:** tests/test_issue_review.py::test_the_verdict_chain_breaks_across_a_stale_gap

### Requirement: A verdict hold has a ceiling

When the chain's age reaches `VERDICT_MAX_HOLD_HOURS` the hold MUST expire: the issue is
no longer held, is back in the pick order, its reason is `verdict-expired`, and the run
says so loudly with the held duration and the ceiling.

#### Scenario: a reviewer re-dates the verdict for 200 h

- **Given** an issue with a verdict label and reviewer markers every 20 h for 200 h, the newest 6 h old
- **When** the queue is built
- **Then** `verdict_expired=1`, `verdict_fresh=0`, `impl_skip=0`, `reason=verdict-expired`, `position=0`, `verdict_held_hours=200`, and the log names the expiry
- **Test:** tests/test_issue_review.py::test_a_reviewer_that_keeps_re_dating_a_verdict_cannot_hold_for_ever
