# host-fleet

## ADDED Requirements

### Requirement: the host fleet copy adds no schedule

The files under `agents/tll-planner/`, `agents/tll-architect/`, `agents/tll-security/`, `agents/tll-reviewer/`, and `agents/tll-implementer/` SHALL carry each lane's soul and skill, SHALL tell that lane not to add or edit a GitHub Actions schedule, and SHALL contain no cron expression.

#### Scenario: the five copies forbid a new schedule

- **GIVEN** the five `SOUL.md` files and the five lane `SKILL.md` files,
- **WHEN** the host-fleet guard reads them,
- **THEN** each one says existing schedules stay as they are, and none contains a cron expression.

- **Test:** `tests/test_host_fleet_souls.py`

### Requirement: the triage planner is the only dispatcher

`agents/README.md` SHALL name `tll-planner` as the triage planner, and every lane soul SHALL say not to recreate `trending-local-llm-issue-implementer`.

#### Scenario: the fleet document names the planner and retires the old profile

- **GIVEN** `agents/README.md` and the five `SOUL.md` files,
- **WHEN** the host-fleet guard reads them,
- **THEN** the readme names `tll-planner` as the triage planner, and each soul says not to recreate the retired profile.

- **Test:** `tests/test_host_fleet_souls.py`
