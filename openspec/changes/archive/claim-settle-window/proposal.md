# Proposal: claim-settle-window

Issue: #1312
PR: #1321

## Why

Two host agents claimed the same issue within one watcher cycle: on #1310 `asimov@mac`
posted a signed status at `2026-11-22T16:05:40Z` and `asimov@omarchy` posted
`claim #1310` at `2026-11-22T16:07:54Z` — 134 s later — while PR #1311 was already in
flight. The duplicate was avoided only because the second host re-read the thread and
withdrew. `AGENTS.md` §7b says a lane "waits and re-reads before starting (race guard)"
but names NO minimum settle time, so a `C:`-marker wake-up can claim on the comment it
just saw while a peer's in-flight claim has not landed yet.

## What Changes

- `AGENTS.md` §7b names **a minimum settle window between a wake-up and a claim**: 180
  seconds, pinned in ONE place, so the wait-and-re-read has a floor instead of being
  however fast the woken host happens to be.
- `scripts/watch_monitor.py` carries that number as `CLAIM_SETTLE_SECONDS` and its
  offline `--check` contract refuses a floor below 60 s, so the pin is load-bearing
  rather than a prose number.
- `tests/test_watch_monitor.py` pins the rulebook needle, the number, and the seam
  constant together, so dropping the row or the pin turns CI red.

## Impact

Rulebook (review-required, rule 3c) plus one script constant and its offline contract.
No workflow, target, data or contract change; the marker protocol is unchanged.

## Not covered

- The other owed §7b row (#1276, a §8 smoke-search guard row) and #1290, whose declared
  row text is missing from its issue body.
- Enforcing the window inside the monitor's diff: the seam is deliberately
  timestamp-free, so the window is a floor the woken lane applies, not a filter on markers.
