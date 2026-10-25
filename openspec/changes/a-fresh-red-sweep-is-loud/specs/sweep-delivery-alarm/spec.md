# sweep-delivery-alarm

## ADDED Requirements

### Requirement: A fresh delivery that did not succeed is a verdict

`sweep_alarm.stale()` MUST return a verdict when the newest delivery is inside
`MAX_AGE_HOURS` but its conclusion is not `success`, marked `fresh: true` and naming the
conclusion. A fresh `success` MUST still return None (health).

#### Scenario: a sweep that failed 30 minutes ago

- **Given** a newest `schedule` delivery 0.5 h old with conclusion `failure`
- **When** `stale()` runs with `max_age_hours=3`
- **Then** it returns a verdict, `fresh` is True, and the reason names `failure`
- **Test:** tests/test_sweep_alarm.py::test_a_red_last_delivery_is_loud_even_when_it_is_FRESH

#### Scenario: a fresh success

- **Given** a newest delivery 0.5 h old with conclusion `success`
- **When** `stale()` runs
- **Then** it returns None
- **Test:** tests/test_sweep_alarm.py::test_a_red_last_delivery_is_loud_even_when_it_is_FRESH

#### Scenario: a cancelled sweep

- **Given** a newest delivery 0.5 h old with conclusion `cancelled`
- **When** `stale()` runs
- **Then** it returns a verdict naming `cancelled`
- **Test:** tests/test_sweep_alarm.py::test_a_red_last_delivery_is_loud_even_when_it_is_FRESH

#### Scenario: the CLI's exit code carries the decision

- **Given** a stub `gh` whose newest delivery is a fresh failure
- **When** the alarm CLI runs
- **Then** it exits 1 and prints FRESH
- **Test:** tests/test_sweep_alarm.py::test_the_cli_exit_codes_are_loud_in_every_direction
