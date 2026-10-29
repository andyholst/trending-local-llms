# fleet-cadence

## ADDED Requirements

### Requirement: every scheduled pipeline runs once a week on Wednesday

Every workflow in `.github/workflows/` with an `on.schedule` MUST name a day-of-week of
`3` (Wednesday) and run at most the stated number of slots in that day. The data gatherer
(`refresh-bot.yml`) is the exception the owner named — it may run TWICE on Wednesday
(`0 6 * * 3` and `43 17 * * 3`), both for the same day. No scheduled pipeline may run on
any other day.

#### Scenario: the gatherer is the exception

- **Given** the fleet's `on.schedule` blocks
- **When** a reader checks the data refresh
- **Then** `refresh-bot.yml` runs exactly twice, both on Wednesday (`0 6 * * 3`,
  `43 17 * * 3`), and no other pipeline runs more than once a week on Wednesday
- **Test:** tests/test_workflows.py (the `refresh: two weekly Wednesday schedule slots`
  check and each pipeline's `* * 3` cron)

#### Scenario: day-of-week is pinned so a regression is caught

- **Given** the repo's workflows
- **When** the suite runs
- **Then** no `- cron:` with a day-of-week other than `3` exists, and every scheduled
  pipeline is gated
- **Test:** tests/test_workflows.py::test_every_bot_guard_with_a_cron_has_the_schedule_bypass
  and the `tests/test_architecture.py` real-repo checks

### Requirement: the alarms measure a WEEK, not an hour or a day

`scripts/sweep_alarm.py` and `scripts/freshness_alarm.py` MUST treat a week as the slot
interval: `sweep_alarm.missed_slots` counts Wednesday deliveries, both alarm CLI defaults
are the weekly window (168 / 170 h), and no "hourly"/"twice-daily" prose or default
survives.

#### Scenario: a missed Wednesday is one missed slot

- **Given** the newest `issue-bot.yml` schedule run
- **When** the alarm measures how many slots should have fired since
- **Then** it counts Wednesdays missed, not hours, and a delivery a week old is still
  fresh while an 8-day-old one is stale
- **Test:** tests/test_sweep_alarm.py::test_a_missed_weekly_slot_is_stale_and_a_fresh_delivery_is_not

#### Scenario: the rules stay in sync with the code

- **Given** AGENTS.md / ARCHITECTURE.md describe the cadence
- **When** they are read
- **Then** they say weekly-Wednesday and never claim an hourly or daily pipeline the
  workflows no longer have, and the `hourly`/`twice-an-hour` language is gone
- **Test:** the architecture-check generated inventory and `tests/test_workflows.py`
