# Proposal: issue-queue-open-pr-window-1324

Issue: #1324
PR: #1325

## Why

`scripts/issue_queue.py::_pulls` asks `gh pr list --state all --limit 100` for PR bodies
even though the only state the implementer predicate consumes is OPEN (`pull` and
`closing_pull` both require it). In a repo with 1300+ PRs the 100-row window is routinely
full of more-recently-updated closed/merged PRs, so a quiet OPEN closing PR falls outside
it. The queue then reports `has_implementer=0` and the fleet sweep re-claims an issue that
already has a live PR — duplicate worktrees and duplicate PRs, the exact failure rule 6j's
implementer window exists to prevent. Observed during the 2026-11-22 fleet triage: the
100-row list carried a stale MERGED row (#1321) while the live closing PRs #1262/#1289
appeared only because they had recent activity.

## What Changes

- `_pulls` requests `--state open` instead of `--state all`: only the state the predicate
  consumes crosses the wire. The `--limit` stays 100, which now comfortably covers the
  open queue.
- `tests/test_issue_queue_predicate.py` plants 100 newer CLOSED PRs plus one older OPEN
  closing PR through a faithful stub `gh` (it honours `--state`, `--limit` and newest-first
  ordering) and proves `_pulls` still receives the live PR. The test is RED on the
  pre-change seam and GREEN after.

## Impact

One `gh` call shape in `scripts/issue_queue.py` plus one regression test. No rulebook,
workflow, target, data or contract change. Payload shrinks: closed PR bodies are no longer
transferred. Complementary to (not duplicating) #1318 / PR #1319, which fixes the separate
state-casing comparison in `build`.

## Not covered

- The state-casing comparison (`== "open"` vs gh's `"OPEN"`) is issue #1318 / PR #1319.
- #1316 is a reviewer ruling on the remaining body width; this change does not decide it.
