# Proposal: cancel-chatter-filer-1741

Issue: #1741

## Why

PR #1673 (fix for #1669) merged at `2026-11-25T05:55:45Z`, yet the sweep at `11:42:24Z` filed #1732 and #1734 from CANCELLED `push`-to-`master` runs whose entire error block is GitHub's own `##[error]The operation was canceled.`. `_superseded_cancelled_push` skips only the unreadable-log (`EMPTY_SHAPE`) case, so a readable log containing nothing but cancellation boilerplate is treated as a real diagnosis. Both filed issues carry a signed handover to `tll-implementer` with nothing to implement.

## What Changes

- Extend `_superseded_cancelled_push` in `scripts/pipeline_failure_issue.py` to skip a cancelled `push`-to-`master` run whose `block` carries no `make` target and only GitHub's cancellation marker (after stripping timestamps and `##[error]` decoration), in addition to the existing `EMPTY_SHAPE` case.
- Keep the #1615 counterexample filing: a cancelled run whose log contains a real `FAIL:`/`##[error]` line with content is NOT skipped.
- Extend `tests/test_pipeline_failure_issue.py` with a RED-first guard using the measured `45556943490` / `45596951334` shape.

## Impact

Filer decision only. No data format, contract, store, README, target or workflow change. The skip is announced with the same `skip N cancelled push-to-master run(s)` line so it is never silent.

## Not covered

- No change to the PR-blockage pass (#1164) or the rediagnosis/attribution passes.
- No rulebook write in a headless leg: the AGENTS.md §8 row this guard owes is declared in `findings/1741.md` as a blocked, review-required row.
- No close of #1732/#1734; those are already-filed artifacts of the defect and are left to the tracker.
