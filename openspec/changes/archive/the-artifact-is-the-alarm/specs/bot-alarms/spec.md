# bot-alarms

## ADDED Requirements

### Requirement: A stale artifact fails the alarm even when no run exists

`make freshness-alarm` MUST measure the newest committed snapshot by the timestamp in its name and
exit non-zero when it is older than `MAX_AGE_HOURS`, naming the age, the newest scheduled refresh
run and the remedy. It MUST exit 2 rather than 0 when there is nothing to measure.

#### Scenario: a fresh snapshot

- **Given** a snapshot written 6 h before the injected clock
- **When** the alarm runs with `MAX_AGE_HOURS=14`
- **Then** it exits 0 and names the snapshot it measured
- **Test:** tests/test_freshness_alarm.py::test_a_fresh_snapshot_passes

#### Scenario: a dropped slot

- **Given** a snapshot 18 h old
- **When** the alarm runs
- **Then** it exits 1, states the age and the window, and says to dispatch refresh-bot
- **Test:** tests/test_freshness_alarm.py::test_a_stale_snapshot_fails_and_names_the_age

#### Scenario: no snapshot at all

- **Given** an empty `data/snapshots/`
- **When** the alarm runs
- **Then** it exits 2 and says there is nothing to measure
- **Test:** tests/test_freshness_alarm.py::test_no_snapshot_at_all_is_never_a_pass

#### Scenario: a touched mtime does not make a stale tree fresh

- **Given** a snapshot whose file mtime is "now" but whose name says 5 days ago
- **When** the alarm runs
- **Then** it still exits 1
- **Test:** tests/test_freshness_alarm.py::test_a_file_mtime_never_makes_a_stale_tree_fresh
