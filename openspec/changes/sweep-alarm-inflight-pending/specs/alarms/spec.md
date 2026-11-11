# alarms

## ADDED Requirements

### Requirement: A delivery still in flight is PENDING, not a failed sweep

When the newest `schedule` delivery has not concluded — its conclusion is `in_progress` or
`queued` — `sweep_alarm.stale` MUST return a **PENDING** verdict, not a failure, while the
delivery is younger than `--inflight-cap-hours` (default 3): the CLI prints it as `PENDING`
naming the in-flight run and exits 0, because a delivery graded while it is mid-flight proves
nothing. The same delivery older than the cap MUST FAIL, named as in flight beyond the cap.
Concluded `failure` or `cancelled` MUST keep the fresh-red verdict of issue #498, and a fresh
`success` stays OK.

#### Scenario: the Wednesday race — the alarm fires while the sweep runs

- **Given** the weekly sweep started at 15:19Z and is still `in_progress`, and the alarm runs at 15:33Z with `--max-age-hours 3`
- **When** `scripts/sweep_alarm.py` runs against that run list
- **Then** the exit code is 0 and the output says `PENDING`, naming the in-flight delivery, with no `FAIL` anywhere
- **Test:** tests/test_sweep_alarm.py::test_an_in_flight_delivery_is_pending_not_a_false_red

#### Scenario: a queued delivery is also in flight

- **Given** the newest delivery concluded `queued` and is 1 h old
- **When** the alarm runs
- **Then** the verdict is PENDING (exit 0), not the #498 fresh-red verdict
- **Test:** tests/test_sweep_alarm.py::test_an_in_flight_delivery_is_pending_not_a_false_red

#### Scenario: a delivery in flight past the cap is hung, and hung is loud

- **Given** the newest delivery started 4 h ago and is still `in_progress`, cap 3 h
- **When** the alarm runs
- **Then** the exit code is 1 and the output names the delivery as in flight beyond the cap
- **Test:** tests/test_sweep_alarm.py::test_an_in_flight_delivery_past_the_cap_is_loud

#### Scenario: a concluded failure keeps its fresh-red verdict unchanged

- **Given** the newest delivery is 30 minutes old and concluded `failure`
- **When** the alarm runs
- **Then** the exit code is 1 with the existing FRESH / “did not drain” render, exactly as issue #498 shipped it
- **Test:** tests/test_sweep_alarm.py::test_a_red_last_delivery_is_loud_even_when_it_is_FRESH
