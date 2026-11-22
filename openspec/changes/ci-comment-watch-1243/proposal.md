# Proposal: ci-comment-watch-1243

Issue: #1243

## Why

The owner directed BOTH machines to be triggered by issue/PR comments AND by CI pipeline
state. asimov@omarchy built a combined watcher (its own cron job `a8229e832be5`); our job
only watched comments. This change brings our job to parity.

## What Changes

- `scripts/watch_monitor.py` + `make watch-monitor`: ONE stable stdout stream of
  `C:<comment id>` and `R:<run id>:<status>:<conclusion>`; any new comment or CI state
  change wakes the agent.
- Rule 6w notes both machines and treats a 0-job `action_required` run as NEVER-STARTED.
- Tests for both wake-up sources and the rulebook/Makefile binding.

## Capabilities

### New Capabilities
- `ci-comment-wakeup`: deterministic dual-source cron change detector.

### Modified Capabilities
- (none)

## Impact

Monitor only; no CI dispatch, no access grants, no store write.
