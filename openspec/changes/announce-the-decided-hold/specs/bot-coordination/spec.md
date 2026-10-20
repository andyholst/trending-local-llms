# bot-coordination

## ADDED Requirements

### Requirement: A decided hold is announced, never expired

An issue carrying a decided label (`agent:refined`, `agent:closed`) MUST be reported by the
shared queue with the timestamp of the verdict marker that applied it, and the sweep MUST
post ONE note per round on it saying that releasing the hold is a human's act with no expiry.

#### Scenario: the measured parked backlog

- **Given** an issue labelled `agent:refined` with an `issue-bot-verdict: refine <TS>` comment
- **When** `make issue-queue` and `make issue-skip-note` run
- **Then** the row reports `decided=agent:refined` and `decided_since=<TS>`, and exactly one note is posted naming the label, the human action, and that the hold has NO expiry
- **Test:** tests/test_issue_review.py::test_a_decided_hold_is_announced_on_the_issue

### Requirement: The implementer's verdict marker is registered

The marker the implementer writes (`issue-bot-verdict`) MUST be declared in the one marker
registry with the rest, so a reader can date it and the round-trip is covered by the guard.

#### Scenario: the marker round-trips through the registry

- **Given** the body `<!-- issue-bot-verdict: refine 2026-10-19T22:35:22Z -->`
- **When** the shared parser reads it
- **Then** it is found as `issue-bot/verdict` with field `refine` and that timestamp, and the start/skip markers still parse unchanged
- **Test:** tests/test_bot_markers.py::test_every_registered_marker_round_trips
