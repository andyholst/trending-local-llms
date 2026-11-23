# Proposal: watch-monitor-comment-fetch-newest-first

Issue: #1360
PR: #1365

## Why

The repo-owned watch monitor's `C:` marker has never fired. `scripts/watch_monitor.py::fetch_payload`
asks GitHub for `issues/comments?per_page=100`, and that endpoint defaults to
`sort=created&direction=asc` — so it returns the 100 OLDEST comments. Measured on
`origin/master`: the cursor froze at `6242933673` (2026-10-17) while the newest repo comment was
`7090680909` (2026-11-23). Every comment after 2026-10-17 was therefore invisible to both hosts'
monitors; the fleet ran on `H:` + `R:` + `M:` only, and a handover posted on a thread was noticed
only at the next 15-minute heartbeat. `tests/test_watch_monitor.py` pinned the pure diff with
synthetic payloads but never the live fetch shape, so the guard was green over a detector that
could not see.

## What Changes

- Ask GitHub for comments newest-first: `per_page=100&sort=created&direction=desc`, from ONE
  seam (`watch_monitor.COMMENT_QUERY`) shared by both `issues` and `pulls` fetches.
- Add a one-time `comments_v2` cursor migration: on the first tick after the repair, seed the
  cursor to the newest id without emitting the stale backlog, so the fix does not wake a lane
  with ~100 old `C:` markers. Subsequent ticks emit only genuinely new comments.
- Drive the REAL `fetch_payload` path in `tests/test_watch_monitor.py` with a stub `gh` CLI that
  answers ascending vs descending queries the way GitHub does; the new guards FAIL on the
  pre-fix code (measured: `repos/o/r/issues/comments?per_page=100`).

## Impact

Fleet-behaviour change only: one repo-owned script and its guard. No data format, contract,
image, Makefile or workflow change. Hosts keep their caller-owned state files; the first tick
after the upgrade baselines the cursor once.

## Not covered

- No change to `R:`/`M:`/`H:` markers — those endpoints already answer newest-first.
- No rebase, merge, master push or CI dispatch; no host profile or access change.
- No change to the cron installation — this fixes the detector the installed wrappers call.
