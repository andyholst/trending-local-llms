# Proposal: comment-monitor-cron-1243

Issue: #1243
PR: #1244

## Why

The first comment trigger missed a deliberate test comment: with no cursor the monitor
read the OLDEST 100 comments, and it ignored comments by our own agent identity. A
trigger that silently drops events is worse than none.

## What Changes

- `scripts/comment_monitor.py` + `make comment-monitor`: baseline the cursor to the
  last 24h once, query newest-first, include EVERY author, emit only sorted comment IDs.
- rule 6w notes the automatic cron trigger; ARCHITECTURE rows and monitor tests.

## Capabilities

### New Capabilities
- `cron-comment-monitor`: deterministic change detection that wakes the comment agent.

### Modified Capabilities
- (none)

## Impact

No store data, no GitHub writes by the monitor, no CI dispatch, no access changes.
