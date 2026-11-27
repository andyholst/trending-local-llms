# Proposal: ghost-run-head-visibility-1797

Issue: #1797

## Why

PR #1770's rebased head `a4e23174` produced two 0-job `action_required` runs (qa-validate
45913406046, pr-closure 45913406044). `auto-merge` had no green check to consume and the PR sat
UNSTABLE. Rule 6w's `R:` duty files only concluded-`failure` runs; `ghost-run-alarm` detects the
0-job shape but its only caller is the owner-dispatched `queued-alarm` sweep; `watch_monitor`
emitted an `R:` marker with `action_required` and no hint that no job ever started. Neither host
could tell "never started" from "slow", and no board item was filed.

## What Changes

- Add a `G:<run id>:<pr>` marker to `scripts/watch_monitor.py` for a completed, zero-job
  `action_required` PR run. It fires ONCE per run, carries the PR identity (including a run whose
  `pull_requests` was cleared after merge), and points the lane at the owner-identity re-push
  remedy in `scripts/ghost_run_alarm.py`.
- Read jobs only for completed `action_required` heads, on the caller's explicit `gh`, with a
  per-tick cap; an unreadable head contributes no marker, never a guess. Reuse the ONE ghost
  verdict (`ghost_run_alarm.ghost_verdict`) instead of a second implementation.
- Add `G:` to the offline marker contract and focused guards for marker shape, once-only
  emission, evidence requirements and the capped job read.

## Impact

No change to the failure-only filing rule, the auto-merge gate, `ghost-verdict` semantics, a data
contract, workflow or schedule. The quiet tick stays silent; a normal `R:` marker keeps its byte
shape. Rulebook rows (§6w/§8) are review-required under rule 3c and are tracked as a blocked task
for the reviewer, not edited by this headless lane.

## Not covered

- No PR is merged by this change; no other branch or PR is touched.
- No new cron, no owner credential on a command line.
