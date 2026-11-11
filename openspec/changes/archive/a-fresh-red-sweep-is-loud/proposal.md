# A sweep that ran and failed is a verdict, not a fresh delivery

**Issue:** [#498](https://github.com/andyholst/trending-local-llms/issues/498)
**Capability:** `sweep-delivery-alarm`

## Why

`scripts/sweep_alarm.py::stale()` answered `None` — "healthy" — for any delivery inside
`MAX_AGE_HOURS`, whatever its conclusion. So the alarm proved the CRON, not the work: a
sweep that is delivered on time and then dies inside `implement` (or is cancelled by
`concurrency: issue-bot-issue-<n>`) is fresh to an age test and reads as green.

Measured today: runs **40190558547** (11:50Z) and **40194644167** (12:46Z) both failed in
`pick`, `implement` was skipped in both, and `sweep-alarm` reported OK each time. The queue
did not drain for two hours and nothing was loud.

The one test that claimed to cover this (`test_a_red_last_delivery_is_named_even_when_it_is_fresh`)
used a delivery 4.8 h old — outside the window — so it exercised the STALENESS path and
passed for the wrong reason.

## What Changes

- **`scripts/sweep_alarm.py`** — inside the window, a conclusion other than `success` is now
  a verdict: `fresh: true`, a reason naming the conclusion, and the run URL. `success` is
  still health; a genuinely old delivery still reports fullness.
- **`render()`** — says the delivery is FRESH and that the queue did not drain, so a reader
  can tell "the cron was dropped" from "the sweep ran and failed".
- **`tests/test_sweep_alarm.py`** — the misleading case is rewritten with a 30-minute-old
  FAILURE (a verdict, `fresh: true`, the reason names it), a fresh SUCCESS is still `None`, a
  fresh `cancelled` is loud, and the CLI is driven end to end for the fresh-red exit code (1).
- **`AGENTS.md`** §8 — the row is owed where the protected-file gate refuses the write; the
  exact text is in `findings.md`.

## Impact

The alarm's decision only. A healthy sweep is still exit 0; a stale one still reports the
missed slots; the new case is "fresh and not successful", which used to be silent.

## Not covered (out of scope)

- The issue's second half — a sweep that dies BEFORE its verdict step posts no comment on the
  issue it picked — is NOT in this change: a new comment marker would have to be registered
  in `scripts/bot_markers.py` **and** in AGENTS.md §6j's table, and that table is a
  protected file whose write is refused here. Closing the gap without the registry line would
  fail `tests/test_bot_markers.py`. Tracked separately.
