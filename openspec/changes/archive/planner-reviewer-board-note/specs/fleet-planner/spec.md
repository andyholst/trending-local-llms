## ADDED Requirements

### Requirement: The planner's board note names PRs awaiting review

The planner skill SHALL require that the board note names every open PR awaiting a first review, with its number, head sha and base, and hands each one to `tll-reviewer` by name.

#### Scenario: A PR awaiting review is named and handed over

- **Given** an open PR whose issue carries no reviewer handover
- **When** the planner posts its board note
- **Then** the note names the PR number, head sha and base and hands it to `tll-reviewer`
- **Test:** tests/test_fleet_handover_protocol.py::test_the_planner_board_note_names_prs_awaiting_review

### Requirement: Review capacity is spent before new PRs are produced

The planner skill SHALL state the dispatch order: an issue with no PR is dispatched to an implementer, while an open PR awaiting review is dispatched to `tll-reviewer` FIRST.

#### Scenario: The dispatch order is stated

- **Given** a board holding both an unclaimed issue and an open PR awaiting review
- **When** the planner decides what to dispatch next
- **Then** the PR is handed to `tll-reviewer` before a new implementer dispatch is made
- **Test:** tests/test_fleet_handover_protocol.py::test_the_planner_board_note_names_prs_awaiting_review
