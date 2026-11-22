# Proposal: queue-open-window

Issue: #1324

## Why

`scripts/issue_queue.py::_pulls` asks `gh pr list --state all --limit 100`, but the only
thing `build` consumes is an **open** PR — both the branch lookup and the closing-PR
lookup require `_is_open`. With `--state all`, up to 100 closed/merged PRs that were
updated more recently than a live closing PR crowd it out of the window, so
`has_implementer` is false and the sweep re-claims an issue that already has an open PR —
duplicate worktrees and duplicate PRs, the exact failure rule 6j's implementer window
exists to prevent. The repo has 1300+ PRs and a busy merge queue, so the window is
routinely full: measured this tick, the 100-row list held stale `MERGED` rows (#1321) while
the live OPEN PRs #1262/#1289 were present only because they had recent activity.

## What Changes

- `_pulls` requests `--state open`, the only state the predicate reads, so a quiet open
  closing PR can never be squeezed out and the payload shrinks (the #1316 cost note).
- `tests/test_issue_queue_predicate.py` plants 150 `MERGED` PRs newer than a live open
  closing PR and proves the open PR is still found — RED on the pre-change `--state all`.

## Impact

One `gh` argument and one guard. No workflow, target, data or contract change; the queue's
behaviour on a normal repo is unchanged.

## Not covered

- #1317 (whether a MERGED closing PR should mark its issue) — a reviewer ruling.
- #1316 (the payload cost) is reduced by this change but its ruling stays open.
