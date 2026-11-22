# Proposal: continuous-queue-1258

Issue: #1258
PR: #1259

## Why

The 2026-11-22 board has 14 open issues already carrying an open PR and 24 with no PR. A lane that finishes one delivery may go quiet while unclaimed work waits, even though the owner's standing directive is to keep working issues/PRs without stopping.

## What Changes

- AGENTS.md §7b: after a delivery a lane re-reads the issue board, claims the oldest unclaimed actionable issue on its own thread when no signed handover exists, and when every open issue has a PR, files a new issue from repository vision with evidence and hands it to `tll-planner`.
- AGENTS.md §8: one regression row.
- `tests/test_continuous_queue_guard.py`: pins both needles, RED on base rulebook.

## Impact

- Rulebook text plus one test module; no workflow, make target, script, data format or CI change.
- Rule 3c review-required, declared on issue #1258 before implementation.

## Not covered

- No change to PR closing keywords, archive rules or fleet profile bytes.
