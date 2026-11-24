## ADDED Requirements

### Requirement: The three measured host-ahead skill notes land additively and exactly once

The planner and reviewer lane skill mirrors SHALL carry the three measured host-ahead pitfall bullets, each exactly once, with no host timestamp header, timestamp or machine name. Copying a whole host file that carried duplicated or interleaved fragments of clauses already on master is NOT a valid landing.

#### Scenario: The planner RESUME note is landed

- **Given** the base skill without the hard-interrupt RESUME bullet
- **When** the change is applied
- **Then** `agents/tll-planner/skills/tll-planner/SKILL.md` carries that bullet exactly once
- **Test:** tests/test_fleet_lifecycle.py::test_fourth_batch_host_ahead_notes_are_landed

#### Scenario: The reviewer read-only and Docker notes are landed

- **Given** the base reviewer skill without the read-only-dispatch and Docker-unset-env bullets
- **When** the change is applied
- **Then** both bullets appear exactly once and the pre-existing `.env` rule is preserved
- **Test:** tests/test_fleet_lifecycle.py::test_fourth_batch_host_ahead_notes_are_landed

#### Scenario: RED on the base tree

- **Given** the base skill files with the new guard present
- **When** the guard runs
- **Then** it fails on each missing needle, and passes once the notes land
- **Test:** tests/test_fleet_lifecycle.py::test_fourth_batch_host_ahead_notes_are_landed
