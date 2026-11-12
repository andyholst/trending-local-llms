# Sweep alarm window follows the weekly sweep

Issue: #804

## Why

`scripts/sweep_alarm.py` was re-tuned for the weekly sweep (issue #801): its
`--max-age-hours` default is 168 (one week plus grace). But the two wiring
halves still hardcode the hourly-era window: the Makefile recipe injects
`--max-age-hours 3` when the caller passes nothing, and `queued-alarm.yml`
calls `make sweep-alarm ... MAX_AGE_HOURS=3`. Against a sweep that asks for
ONE delivery per Wednesday, a 4.2 h gap between deliveries is guaranteed red
— measured: `make sweep-alarm REPO=andyholst/trending-local-llms` fails with
"the newest delivery is 4.2 h old (max 3.0 h)" on a healthy weekly cadence.
An alarm that cries on the normal schedule is the #801 failure mode wearing a
different hat: the real drop stops standing out.

## What Changes

- The Makefile `sweep-alarm` recipe forwards `MAX_AGE_HOURS` only when the
  caller supplies one; otherwise the script's own weekly default governs —
  ONE implementation of the window (rule 6d).
- `queued-alarm.yml` drops its `MAX_AGE_HOURS=3` override.
- The script's `--max-age-hours` help text says 168 (the docstring already does).
- Two wiring tests lock the shape.

## Impact

- `make sweep-alarm`, `.github/workflows/queued-alarm.yml`, `scripts/sweep_alarm.py`,
  `tests/test_sweep_alarm.py`, AGENTS.md guard row.

## Not covered

- `freshness-alarm`'s `MAX_AGE_HOURS=14` is a different alarm (the weekly
  refresh snapshot, issue #452) — its window matches its cadence and stays.
- The cadence itself (Wednesday slots) is unchanged and already pinned by
  `test_the_sweep_carries_a_second_slot_and_the_alarm_is_wired`.
