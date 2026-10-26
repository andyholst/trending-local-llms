# The alarm reads the artifact, not the run

**Issue:** [#452](https://github.com/andyholst/trending-local-llms/issues/452)
**Capability:** `bot-alarms`

## Why

On 2026-10-20 the **06:00 refresh never started at all**, and nothing said so. `refresh-bot` runs
twice a day (`06:00` + a `17:43` backup) precisely because GitHub delays or drops on-the-hour crons
— and every alarm in this repository watched a run that EXISTS: `queued-alarm` reads a stuck queue,
`sweep-alarm` a delivery, `bot-health` the runs a pipeline did produce. **A run GitHub never created
has no row to read.**

The blast radius is the product: with the backup at 17:43 a dropped `06:00` leaves the index up to
**11.7 h stale**, and the whole fleet reports green while the visible artifact ages.

## What Changes

- **`scripts/freshness_alarm.py`** — measures the newest committed snapshot (`data/snapshots/
  trending-<YYYYMMDD>-<HHMMSS>.json`, the timestamp **in its name**, never the file's mtime: a
  checkout's mtime is the clone time) and fails when it is older than `MAX_AGE_HOURS` (**14** — one
  missed slot allows the ~11.7 h gap a twice-daily cron leaves), naming the age, the newest
  **scheduled** `refresh-bot` run (so "the cron never started" is distinguishable from "it ran and
  produced nothing") and what to do.
- No snapshot at all, or an unreadable one, exits **2** — a blind read is never health.
- **`make freshness-alarm [REPO= MAX_AGE_HOURS=]`**.
- **`queued-alarm.yml`** gains the step **after** its sweep alarm: that workflow already runs twice
  an hour behind the owner/collaborator guard with the default token, so no sixth pipeline is needed.
- **`tests/test_freshness_alarm.py`** — an injected `--now` (never the wall clock, the #88 defect):
  fresh passes, stale fails naming the age and the remedy, the NEWEST filename wins, no snapshot is
  exit 2, and a touched **mtime** never makes a stale tree look fresh.

## Impact

A dropped refresh slot now reds a sweep within hours, naming the artifact's age and the last run —
instead of waiting for someone to notice the README's header.

## Not covered (out of scope)

- It reports; it does not dispatch the refresh. The issue's "or comments" alternative would need the
  marker-dedup machinery of `queued-alarm`, and a red sweep is already loud.
- Only the SNAPSHOT is measured. The README's own `Last generated:` line could drift from it; that is
  a separate check (`check_readme_generated` already refuses a hand-edited README).
