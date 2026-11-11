# alarms

## ADDED Requirements

### Requirement: A red push-to-master qa-validate run goes red on the schedule

`make master-alarm` MUST read the newest `push`-to-master `qa-validate` run and exit 1 naming the
run URL and the failing jobs when it concluded in failure; a green, pending or absent run is not
an alarm, and an unreadable GitHub read exits 2 rather than reporting a pass.

#### Scenario: a red run is reported

- **Given** a recorded newest push-to-master qa-validate run that concluded in failure
- **When** `scripts/master_alarm.py` reads it
- **Then** it exits 1 naming the run URL and each failing job
- **Test:** tests/test_master_alarm.py::test_a_red_run_is_reported

#### Scenario: green, pending or absent is not an alarm

- **Given** fixtures where the newest push-to-master run is success, in progress, or does not exist
- **When** the alarm reads each
- **Then** exit status is 0 and no alarm line is printed
- **Test:** tests/test_master_alarm.py::test_a_green_or_pending_or_absent_run_is_not_an_alarm

### Requirement: Every deterministic gate of the validate job has a named repairer

Every gate (make target) the `validate` job runs MUST appear on the alarm's KEEPER list
(`architecture-bot` repairs it) or its ALARM list (this alarm covers it) — a new gate that lands
on neither is a defect.

#### Scenario: the gate lists cover the real validate job

- **Given** the repository's `qa-validate.yml` `validate` job and `scripts/master_alarm.py`'s registry
- **When** the registry test reads both
- **Then** every validate gate is on exactly one of the two lists
- **Test:** tests/test_master_alarm.py::test_every_validate_gate_is_on_a_list

#### Scenario: every validate step target is a gate of the job

- **Given** the `validate` job's step list
- **When** the registry test expands each step's `make` target
- **Then** each target is a gate the registry knows
- **Test:** tests/test_master_alarm.py::test_every_validate_step_target_is_a_gate_of_the_validate_job

### Requirement: The alarm is wired through the Makefile behind the guard

`queued-alarm.yml` MUST run `make master-alarm REPO=…` (never the script directly) after its
guard, so the scheduled sweep goes red when master is red.

#### Scenario: the workflow guards first and calls the make target

- **Given** `.github/workflows/queued-alarm.yml`
- **When** the wiring test reads the `alarm` job
- **Then** `guard` runs first and the step calls `make master-alarm`, and the Makefile target forwards `REPO`/`LIMIT`
- **Test:** tests/test_master_alarm.py::test_the_workflow_guards_first_and_calls_the_make_target

### Requirement: The rulebook carries the rule and the guard row

`AGENTS.md` MUST state the red-master alarm rule (naming `make master-alarm` and
`scripts/master_alarm.py`) and its §8 regression-guard row naming this test.

#### Scenario: the rule and the guard row are present

- **Given** the repository's `AGENTS.md`
- **When** the guard test reads it
- **Then** the rule text, the make target, the script and the §8 row naming this test are all named
- **Test:** tests/test_master_alarm.py::test_agents_md_carries_the_rule_and_the_guard_row
