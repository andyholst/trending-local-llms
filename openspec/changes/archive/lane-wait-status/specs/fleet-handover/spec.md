## ADDED Requirements

### Requirement: A waiting lane posts a host-stamped status on the issue thread

Every TLL lane SHALL post a status comment on the issue's OWN thread before it
starts, while a test or CI gate runs, and at handover. The note SHALL name the
machine as `user@hostname`, state what the lane is doing, what it is waiting for
and which issue or PR it can help with next. It SHALL NOT replace the claim, the
PR comment or the `done #<id> · handover <...>` comment, and SHALL NOT claim an
issue another machine owns.

#### Scenario: A lane waits on a gate with a visible status

- **Given** a lane has a test run or a CI pipeline in flight
- **When** the other host reads the newest comments on the issue thread
- **Then** it finds a signed status comment with the `user@hostname` machine
  tag, the current work, the waited-for gate and the next issue/PR the lane can
  help with
- **Test:** tests/test_fleet_handover_protocol.py::main

#### Scenario: A lane drops the waiting rule

- **Given** one of the seven `tll-*/SOUL.md` files or the planner skill is
  edited to remove the status rule or the host stamp
- **When** `python3 tests/test_fleet_handover_protocol.py` runs
- **Then** it fails with the lane and the dropped needle named, and `make test`
  is red on the PR
- **Test:** tests/test_fleet_handover_protocol.py::main

### Requirement: The rule lives in every lane and in the planner skill

The seven lane SOULs and `agents/tll-planner/skills/tll-planner/SKILL.md` SHALL
each carry the status rule and the `user@hostname` stamp, and the planner SHALL
read the status notes when delegating.

#### Scenario: All eight instruction files carry the rule

- **Given** the repository's `agents/` tree at this change
- **When** the protocol guard scans all seven SOULs and the planner skill
- **Then** every file passes the status-rule and host-stamp assertions
- **Test:** tests/test_fleet_handover_protocol.py::main
