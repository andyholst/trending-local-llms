# Proposal: freshness-alarm-window-follows-cadence

Issue: #1031
PR: #1034

## Why

`queued-alarm.yml` runs `make freshness-alarm … MAX_AGE_HOURS=14` with the comment
"Twice-daily crons leave a ~11.7 h gap; 14 h is one missed slot" — wording from the
hourly era. `refresh-bot.yml` has been weekly since issues #670–#677
(`'0 6 * * 3'` + backup `'43 17 * * 3'`), and `scripts/freshness_alarm.py` already
carries the weekly default `DEFAULT_MAX_AGE_HOURS = 170` (a week + a day). Measured
2026-11-15: a dispatch-only `queued-alarm` run (43714924448) would go red at the
freshness step on an ordinary 3-day-old weekly snapshot — an alarm whose window
contradicts the cadence it watches cries the wrong wolf, exactly the class issue
#804 removed for `sweep-alarm` ("the Makefile forwards `MAX_AGE_HOURS` only when
supplied and `queued-alarm.yml` carries no window literal").

## What Changes

- `queued-alarm.yml`'s freshness step drops the `MAX_AGE_HOURS=14` override: the
  window is `freshness_alarm.py`'s own weekly default (one implementation, rule 6d).
- `tests/test_freshness_alarm.py` pins it: no window literal in the workflow step or
  the Makefile recipe, a 165 h weekly gap passes the default window, and a
  180 h age (one missed weekly slot) goes red naming the 170 h window.
- AGENTS.md §8 gains the guard row.

## Impact

- Alarms: `queued-alarm`'s freshness gate stops red-ing on the normal weekly cadence;
  a genuinely missed week still goes red.

## Not covered

- Making the window DERIVED from the refresh cron text (the alarm's default is
  already weekly; deriving it dynamically is a separate change).
- `queued-alarm`'s cadence itself (owner-dispatched by #1029; finding #1032 owns that
  decision).
