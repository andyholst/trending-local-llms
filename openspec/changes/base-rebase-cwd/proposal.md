# Proposal: base-rebase-cwd

Issue: #1330

## Why

`scripts/worktree_base.py::mode_rebase` reads the head it rebases from `os.getcwd()` and
never checks that the current HEAD **is** the named branch. Run from any other checkout
(the shared main clone, a second lane's worktree) it therefore reports the wrong head and
answers `rebase=up-to-date` for a branch that is dozens of commits behind — a silent skip in
a seam whose own docstring promises "Never a lost commit, never a silent skip".

Measured A/B on 2026-11-22, branch `ci/pr-block-log-budget-1174`, base `4818433`:

- from the main checkout (HEAD = `master`): `behind_base=0`, `rebase=up-to-date`, while the
  branch is **29 commits behind**;
- from that branch's own worktree: `behind_base=29`, `ahead_base=3`, `rebase=conflict`.

A fleet leg that runs the §6s repair from the shared clone — the natural place — silently
no-ops and leaves the PR `DIRTY` with no checks running.

## What Changes

- `mode_rebase` extends its existing detached-HEAD/base-branch guard: when the named branch
  is not the checked-out HEAD, it REFUSES with the remedy, never reporting `up-to-date`.
- `tests/test_worktree_base.py` gains the A/B case: the real CLI run twice, once from the
  branch worktree and once from a second worktree on `master`, asserting the second is
  refused while the first reports the true `behind_base`.

## Impact

One guard in one script plus its test. The exit-code contract is unchanged
(0 up-to-date/rebased, 3 conflict, 1 refused, 2 usage), so every caller keeps its meaning.

## Not covered

- The other modes (`check`, `advance`, `adopt`): `mode_adopt` already refuses a branch
  carrying commits the base lacks, and the issue scopes this to `rebase`.
