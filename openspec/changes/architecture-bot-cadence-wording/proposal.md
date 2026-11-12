# architecture-bot wiring text states the cadence it actually runs

**Issue:** #860
**PR:** [#862]
**Capability:** `architecture-bot-cadence` (the schedule wiring of
`architecture-bot.yml`, its explanatory comment, and the test label that
explains the slot).

## Why

`architecture-bot.yml` runs `13 * * * 3` — Wednesday once a week — but the
comment above the cron still reads "HOURLY, an odd minute (issue #526)", and
`tests/test_architecture_bot.py` labels its cron assertion "the slot is
HOURLY, so a stale index converges in an hour". Both strings stayed green
while the owner's once-per-week directive (issues #670–#677, pinned by
`tests/test_workflows.py::test_every_pipeline_runs_weekly_on_wednesday`)
moved the cadence. The comment is the ONLY explanation of why the minute is
odd: a maintainer restoring "hourly" from it would break the pinned cadence
while every gate stays green, and a green test whose label describes the
opposite schedule misleads every future reader of the wiring.

## What Changes

- The schedule comment in `.github/workflows/architecture-bot.yml` states the
  Wednesday weekly cadence and keeps the odd-minute rationale (GitHub delays
  and drops on-the-hour crons — the measured `sweep-alarm` class, issue #497).
- The test label in `tests/test_architecture_bot.py` states the same truth:
  a Wednesday weekly slot at an odd minute.
- A regression guard (`test_the_schedule_comment_names_the_cadence_it_pins`)
  refuses wiring text that claims an hourly slot while the pinned cron is a
  Wednesday day-of-week; the guard is proven against the OLD comment text
  (rule 6c: it FAILS on `git show origin/master:.github/workflows/architecture-bot.yml`).

## Impact

- `tests/test_architecture_bot.py` — one new guard; one relabeled check.
- `.github/workflows/architecture-bot.yml` — comment only; no trigger change.
- No behavior, no target, no pipeline-job change: AGENTS.md needs no row (rule 3c).

## Not covered

- #861 (the ARCHITECTURE.md half of the generated pair has no event-driven
  keeper) is a separate change and stays its own issue.
- The cron expression itself is already correct and is NOT touched.
