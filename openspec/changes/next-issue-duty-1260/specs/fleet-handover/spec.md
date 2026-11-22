## ADDED Requirements

### Requirement: A delivery is followed by the next claim or a filed issue

After a lane posts its delivery/handover for an issue, it MUST re-read the issue board
and either sign a claim on the oldest unclaimed actionable issue (starting it in its own
worktree) or, when every open issue is claimed or already has a PR, file an
evidence-backed issue and post a signed handover to `tll-planner`. A `done` comment
followed by silence is not a delivery.

#### Scenario: The rulebook names the post-delivery duty

- **Given** the fleet rulebook in `AGENTS.md` §7b
- **When** a lane finishes a delivery and re-reads the board
- **Then** §7b requires a claim on the oldest unclaimed actionable issue, or an
  evidence-backed issue with a `tll-planner` handover when nothing is unclaimed
- **Test:** `tests/test_fleet_handover_protocol.py::test_next_issue_duty_is_documented`

#### Scenario: Every lane SOUL carries the duty

- **Given** the seven `tll-*` lane `SOUL.md` files
- **When** a lane reads its own operating instructions after a delivery
- **Then** each file states the re-read-and-claim-or-file duty in the same words
- **Test:** `tests/test_fleet_handover_protocol.py::test_next_issue_duty_is_documented`

#### Scenario: The planner skill carries the duty

- **Given** the planner's own skill
- **When** the planner dispatches after a delivery
- **Then** it can read the next claim or the filed-issue handover from the board
- **Test:** `tests/test_fleet_handover_protocol.py::test_next_issue_duty_is_documented`
