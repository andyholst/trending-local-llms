# bot-coordination

## ADDED Requirements

### Requirement: A missed sweep delivery is loud

The sweep MUST carry more than one schedule slot, and `make sweep-alarm` MUST fail when the newest
`issue-bot` `schedule` run is older than `MAX_AGE_HOURS` (default 3), when no schedule run has ever
been delivered, and when the GitHub read fails — while a fresh delivery MUST pass.

#### Scenario: the measured 3-6 h gap

- **Given** the recorded deliveries (`01:41:54`, `22:24:00` FAILED, `18:31:58`, `13:39:43`, `07:44:08`)
- **When** `make sweep-alarm` measures them at `06:30Z`, `MAX_AGE_HOURS=3`
- **Then** it exits 1, names 4.8 h of age, 5 missed `:19` slots and the real gaps, and the last conclusion
- **Test:** tests/test_sweep_alarm.py::test_the_measured_gaps_are_stale_and_a_fresh_delivery_is_not

#### Scenario: a delivery inside the window

- **Given** a delivery 48 minutes old
- **When** `make sweep-alarm` runs
- **Then** it exits 0 and prints OK
- **Test:** tests/test_sweep_alarm.py::test_the_cli_exit_codes_are_loud_in_every_direction

#### Scenario: no delivery at all

- **Given** an empty `schedule` run list
- **When** the alarm measures it
- **Then** it is a verdict naming the cron, never a pass
- **Test:** tests/test_sweep_alarm.py::test_no_delivery_at_all_is_a_verdict_and_never_a_pass

#### Scenario: the alarm cannot read GitHub

- **Given** a `gh` that fails
- **When** the alarm runs
- **Then** it exits 2 with FAIL on stderr, so a broken read is never a silent green
- **Test:** tests/test_sweep_alarm.py::test_the_cli_exit_codes_are_loud_in_every_direction

#### Scenario: the wiring raises no dead code

- **Given** the sweep workflow, the Makefile and the alarm pipeline
- **When** the wiring test reads them
- **Then** the sweep has two slots, `make sweep-alarm` exists and calls the script, and the alarm job calls it after its checkout
- **Test:** tests/test_sweep_alarm.py::test_the_sweep_carries_a_second_slot_and_the_alarm_is_wired
