## ADDED Requirements

### Requirement: The three lane skill mirrors carry the owner-authorised host-ahead clauses

The repository SHALL track the host-ahead text of the planner, implementer and reviewer lane skills, so that re-provisioning a host from `master` cannot silently drop the forward clauses the owner authorised on #1745.

#### Scenario: Every landed clause family is present

- **Given** the three tracked lane skill mirrors at this PR's head
- **When** `tests/test_fleet_lifecycle.py` runs
- **Then** the planner CI-only/readback, sha-measurement, bounded-resume, DIRTY re-cut, parallel-lane, chat-status, pr-closure invocation and PR-rebinding clauses, the implementer `master_alarm.py::GATES` and cherry-pick replay clauses, and the reviewer lane-SKILL-rewrite and escaped-backtick clauses are all present
- **Test:** tests/test_fleet_lifecycle.py::test_host_ahead_lane_skill_clauses_are_landed

#### Scenario: The guard would fail on the base mirrors

- **Given** the three skill mirrors from the fetched `origin/master`
- **When** the same guard reads them
- **Then** it fails on every landed clause, proving it locks the landing rather than a pre-existing property
- **Test:** tests/test_fleet_lifecycle.py::test_host_ahead_lane_skill_clauses_are_landed

### Requirement: The skill landing does not drop an existing pinned needle

The landing SHALL be non-breaking for guards that read these skills: every base reference those guards pin remains, with the single documented exception of the planner's local render-probe prose superseded by the CI-only readback rule.

#### Scenario: Existing host-note pins stay green

- **Given** the modified mirrors at this PR's head
- **When** `test_lane_skill_mirrors_carry_landed_host_ahead_notes` reads them
- **Then** every previously landed host note and its issue reference — including `#1115` — is still present, and the guard exits zero
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes
