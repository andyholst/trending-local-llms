## ADDED Requirements

### Requirement: The planner skill states the DEAD-lane RESUME rule

The tracked `tll-planner` skill SHALL state that a pushed branch with no pull request is a DEAD lane and SHALL require a bounded RESUME rather than a second implementation, including three pre-dispatch checks: a live lane process, an existing PR lookup, and whether the pushed commit already carries the full delivery.

#### Scenario: The tracked planner skill carries the rule

- **Given** the tracked skill at `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** the offline guard reads it
- **Then** the DEAD-lane clause and all three checks are present and no duplicate section heading was introduced
- **Test:** tests/test_dead_lane_resume.py::test_planner_skill_states_dead_lane_resume
