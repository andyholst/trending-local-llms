## ADDED Requirements

### Requirement: A delivery is not a stopping point

After a delivery, the rulebook SHALL require a lane to re-read the issue board and, absent a signed handover to another lane, claim the oldest unclaimed actionable issue with a signed comment on that issue's own thread.

#### Scenario: An issue already has a PR

- **Given** a lane just posted its `done`/`pr` handover and the board has other unclaimed issues
- **When** the lane looks for its next task
- **Then** AGENTS.md §7b requires it to claim the oldest unclaimed actionable issue on that issue thread
- **Test:** tests/test_continuous_queue_guard.py::test_rulebook_carries_continuous_queue_rule

### Requirement: Innovation when the queue is fully covered

When every open issue already has a PR, the rulebook SHALL require a new issue filed from the repository vision with evidence, handed to `tll-planner`.

#### Scenario: No unclaimed issue exists

- **Given** every open issue already carries an open PR
- **When** a lane has finished its delivery
- **Then** AGENTS.md §7b requires a new evidence-backed issue and a planner handover rather than idling
- **Test:** tests/test_continuous_queue_guard.py::test_rulebook_carries_innovation_rule

### Requirement: Guard row names the test

AGENTS.md §8 SHALL carry a row naming this module.

#### Scenario: The guard row is dropped

- **Given** the §8 table
- **When** the module checks it
- **Then** a missing row is a loud failure
- **Test:** tests/test_continuous_queue_guard.py::test_rulebook_carries_guard_row
