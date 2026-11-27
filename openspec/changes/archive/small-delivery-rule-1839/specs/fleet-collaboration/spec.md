# fleet-collaboration

## ADDED Requirements

### Requirement: the canonical protocol states the #690 small non-breaking delivery rule

`docs/fleet-collaboration.md` MUST state, in its PR-delivery item (section 4, item 4), that every PR is a small, single-purpose, non-breaking delivery for one issue (#690): no schema, contract, API, table or data-shape break, no unrelated churn, no dead code, and that a breaking change MUST be split or flagged on the issue before writing. The statement MUST be pinned by a distinctive needle in `COLLAB_NEEDLES` in `tests/test_fleet_lifecycle.py`; the existing guard that iterates that tuple MUST fail when the statement is absent from the document.

#### Scenario: a new bot reads the delivery rule

- **Given** a reader of the canonical `docs/fleet-collaboration.md` who has never seen `AGENTS.md` or a lane SOUL
- **When** they reach the PR-delivery item (section 4, item 4)
- **Then** they find the #690 rule — small, single-purpose, non-breaking, one issue per PR, breaking changes split or flagged before writing — and know not to bundle a schema or data-shape change into a doc PR
- **Test:** tests/test_fleet_lifecycle.py::test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol

#### Scenario: dropping the sentence reddens the guard

- **Given** the `COLLAB_NEEDLES` tuple contains the distinctive #690 small-delivery needle
- **When** the canonical document does not carry that sentence
- **Then** `test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol` names the missing needle and fails, so the rule cannot be silently dropped
- **Test:** tests/test_fleet_lifecycle.py::test_the_canonical_collaboration_doc_covers_every_lane_and_the_board_protocol
