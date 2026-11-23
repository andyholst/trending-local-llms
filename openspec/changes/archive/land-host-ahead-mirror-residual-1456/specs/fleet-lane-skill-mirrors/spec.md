## ADDED Requirements

### Requirement: Each mirror gains only host-ahead lines and loses no master text

Every `agents/<lane>/skills/<lane>/SKILL.md` mirror SHALL keep master's text
verbatim and gain only the host-only notes measured against the fetched base, so
the branch diff is additive (rule 3b) and the lane's pinned rules survive.

#### Scenario: The mirror diff is purely additive

- **Given** the PR head and its base `origin/master`
- **When** the four mirrors are diffed base-to-head
- **Then** every changed hunk is an insertion or a host-superset replacement of one
  wording line, and no master-only line disappears
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

#### Scenario: Master's pinned push-and-verify rules are intact

- **Given** the PR head's planner and implementer mirrors
- **When** `tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule` runs
- **Then** it reports 0 failures — the `#1423`/`#1427` content the host copies lack
  is still present
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule

### Requirement: Landed host notes carry no machine name or host timestamp

The reconciled mirrors SHALL NOT carry the host's machine name, its
`## Host notes ahead of master` timestamp header, or a host timestamp, because
the tree is shared across machines.

#### Scenario: The reviewer mirror carries no machine name

- **Given** the PR head's `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`
- **When** the guard reads it
- **Then** it carries no `asimov@mac` spelling and no host timestamp header
- **Test:** tests/test_fleet_lifecycle.py::test_reviewer_skill_carries_landed_host_ahead_notes

#### Scenario: A refreshed host reaches zero divergences

- **Given** a host profile home whose lane skills equal this tree's bytes
- **When** `make fleet-host-sync-check BASE=HEAD PROFILES_HOME=<that home>` runs
- **Then** it prints the OK line with 0 divergences across all eight lanes
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
