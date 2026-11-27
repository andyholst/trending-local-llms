# fleet-collaboration

## ADDED Requirements

### Requirement: the canonical protocol states the both-required close-hygiene rule

`docs/fleet-collaboration.md` MUST state, in its PR-delivery item, that a fleet PR's title carries the change and `Closes #<id>`, and that the PR body repeats its own `Closes #<id>` line — never title-only, never body-only — so the squash merge closes the bound issue. The statement MUST be pinned by a needle in `COLLAB_NEEDLES` in `tests/test_fleet_lifecycle.py`; the existing guard that iterates that tuple MUST fail when the statement is absent from the document.

#### Scenario: a new bot reads where the closing keyword belongs

- **Given** a reader of the canonical `docs/fleet-collaboration.md` who has never seen `AGENTS.md` or a lane SOUL
- **When** they reach the PR-delivery item (section 4, item 4)
- **Then** they find the both-required rule — title carries `Closes #<id>`, body repeats its own `Closes #<id>` line, never title-only or body-only — and understand that the squash closes the bound issue
- **Test:** tests/test_fleet_lifecycle.py::test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol

#### Scenario: dropping the sentence reddens the guard

- **Given** the `COLLAB_NEEDLES` tuple contains the close-hygiene needle
- **When** the canonical document does not carry that sentence
- **Then** `test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol` names the missing needle and fails, so the contract cannot be silently dropped
- **Test:** tests/test_fleet_lifecycle.py::test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol
