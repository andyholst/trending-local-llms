# alarms

## ADDED Requirements

### Requirement: the sweep alarm derives the owed-delivery mode from the workflow tree

`make sweep-alarm` MUST decide whether a weekly delivery is owed by reading the sweep
pipeline's own trigger surface (`workflow_declares_schedule` over
`.github/workflows/issue-bot.yml`), never by assuming a cadence. In SCHEDULED mode the
measured weekly semantics are unchanged (a missed Wednesday slot is stale; in-flight is
PENDING up to the cap and HUNG past it). In DISPATCH-ONLY mode the absence of any delivery
is not a failure — a dispatch-only sweep owes no slot — while a delivery that concluded
FAILED, or one still in flight past the in-flight cap, still goes red. The mode is derived
from the tree so the alarm can never disagree with the workflow it watches.

#### Scenario: a dispatch-only sweep owes nothing by age alone

- **Given** `issue-bot.yml` with no `schedule:` block
- **When** `make sweep-alarm` evaluates the newest deliveries
- **Then** "no delivery owed" reports OK (exit 0), naming the dispatch-only mode
- **Test:** tests/test_sweep_alarm.py::test_a_dispatch_only_sweep_owes_no_weekly_slot

#### Scenario: a failed or hung dispatch still reds the alarm

- **Given** the same dispatch-only mode
- **When** the newest dispatched delivery concluded FAILED, or is still in flight past the
  in-flight cap
- **Then** the alarm exits 1 naming it (`hung=True` for the in-flight case)
- **Test:** tests/test_sweep_alarm.py::test_a_dispatch_only_sweep_owes_no_weekly_slot and
  tests/test_sweep_alarm.py::test_an_in_flight_delivery_past_the_cap_is_hung_and_loud

#### Scenario: scheduled-mode weekly semantics stay pinned

- **Given** a sweep pipeline that DOES declare a schedule
- **When** the alarm runs with the weekly window
- **Then** a missed weekly slot is stale-red and a fresh delivery is not, exactly as the
  scheduled-mode tests pin
- **Test:** tests/test_sweep_alarm.py::test_a_missed_weekly_slot_is_stale_and_a_fresh_delivery_is_not
