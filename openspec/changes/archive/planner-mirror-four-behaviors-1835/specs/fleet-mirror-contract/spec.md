## ADDED Requirements

### Requirement: The in-tree planner mirrors carry the four standing fleet behaviors

The repository SHALL track the four owner-authorised standing behaviors in the planner's in-tree
`SOUL.md` and skill mirror, so a planner re-provisioned from `master` sees the same contract as the
canonical collaboration doc.

#### Scenario: The SOUL names all four behaviors

- **Given** `agents/tll-planner/SOUL.md` at this PR's head
- **When** the mirror is read for the "four instances", autonomous pick-up, weekly pass and per-host sync contract
- **Then** it carries "four instances of each delegable lane", "pick work up autonomously from the issue comments", "weekly lane-maintenance pass" and "Per-host sync check runs from every LLM host", with the cadence-not-timer and no-stamp-wipe limits intact
- **Test:** tests/test_fleet_lifecycle.py::test_every_lane_carries_the_live_pr_preflight

#### Scenario: The skill carries the matching guidance blocks

- **Given** `agents/tll-planner/skills/tll-planner/SKILL.md` at this PR's head
- **When** the planner reads its skill for fleet scale and host-sync guidance
- **Then** the "Fleet scale + autonomous pick-up" and "Per-host sync check" sections are present, and the pre-existing PARALLEL dispatch rule and its host-stamp ban are unchanged
- **Test:** tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owners_parallel_dispatch_rule

### Requirement: The mirror update is purely additive

The refresh SHALL add the four clause groups without deleting or duplicating any landed mirror text.

#### Scenario: No clause grows past the pinned union base

- **Given** the pinned pre-union base blobs for the four fleet mirrors
- **When** `tests/test_fleet_lifecycle.py` compares each mirror's non-trivial lines and clauses
- **Then** no unit's copy count grows, and the planner SOUL/skill diff has zero deleted lines
- **Test:** tests/test_fleet_lifecycle.py::test_mirror_unions_add_no_duplicate_or_interleaved_bullets
