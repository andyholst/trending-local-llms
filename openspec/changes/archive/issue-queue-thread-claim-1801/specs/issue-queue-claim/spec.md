## ADDED Requirements

### Requirement: A signed thread claim holds the issue from the sweep

`issue_queue.build` SHALL treat the newest ACTIVE signed `BOT <lane> · working on #<n>` claim on an
issue's own thread as an implementer for the same window it applies to implementer activity
(`gap_hours`), so a sweep cannot pick an issue another lane has claimed. The claim SHALL be read
through the ONE parser in `dispatch_guard`; no second marker grammar SHALL be introduced.

#### Scenario: A fresh thread claim removes the issue from the pick order

- **Given** a stubbed GitHub issue carrying a signed `BOT tll-implementer (host asimov@omarchy) · working on #1176` comment created minutes before now
- **When** `issue_queue.build` computes the queue
- **Then** #1176 has no row at `position=0` (it is skipped like a branch or an open closing PR)
- **Test:** tests/test_issue_queue_predicate.py::test_a_thread_claim_hides_an_issue_from_the_sweep

#### Scenario: A stale claim releases the issue

- **Given** a signed working-claim older than the `gap_hours` window
- **When** `issue_queue.build` computes the queue
- **Then** #1176 is present with `has_implementer=0`
- **Test:** tests/test_issue_queue_predicate.py::test_a_stale_thread_claim_releases_the_issue

#### Scenario: A released claim does not hold

- **Given** a working-claim followed by a signed `done #1176` release on the same thread
- **When** `issue_queue.build` computes the queue
- **Then** #1176 is present with `has_implementer=0`
- **Test:** tests/test_issue_queue_predicate.py::test_a_released_thread_claim_does_not_hide_the_issue

#### Scenario: A claim on another issue is not this issue's implementer

- **Given** a signed working-claim naming #1175 only
- **When** `issue_queue.build` computes the queue for #1176
- **Then** #1176 is present with `has_implementer=0`
- **Test:** tests/test_issue_queue_predicate.py::test_a_claim_on_another_issue_does_not_hide_this_one

### Requirement: The claim grammar has one home

`issue_queue.py` SHALL call `dispatch_guard.comment_markers` (through its `active_claim` /
`normalize_comments` seam) and SHALL NOT define its own claim regex.

#### Scenario: The one parser is reused

- **Given** the source of `scripts/issue_queue.py`
- **When** the claim-reading code is inspected
- **Then** it reads `dispatch_guard.active_claim` and contains no hand-rolled `working on` pattern of its own
- **Test:** tests/test_issue_queue_predicate.py::test_the_one_claim_parser_is_reused_not_a_hand_rolled_regex
