# Proposal: base-rebase-invocation-dir-1335

Issue: #1335
PR: #1342

## Why

The §6s failed-rebase announcement tells a lane to run `make worktree-resume BRANCH=<b>`
and then `make base-rebase BRANCH=<b>` — but it never names the directory to run the second
command from. `base-rebase` resolves the head it rebases from `HEAD` of the invocation
directory (fixed for `mode_rebase` by #1330/#1333), so a lane that follows the remedy from
the shared main clone — which sits on `master`, the natural place — gets `rebase=up-to-date`
for a branch that is actually behind, and the PR stays DIRTY with no checks running. The
refusal added by #1330 is correct; the documented remedy is what still sends the caller to
the wrong checkout.

## What Changes

- `scripts/pr_health.py::rebase_comment_body` names the branch worktree explicitly in the
  failed-rebase announcement: `cd <worktree for <branch>>` is the invocation dir for the
  `make base-rebase` step that follows `worktree-resume`.
- `tests/test_pr_health.py::test_a_failed_rebase_round_announces_on_the_pr_thread_once`
  asserts the posted comment names that invocation directory, so a future edit cannot drop
  the only clue that keeps the §6s remedy usable.

## Impact

Comment text only. Rebase decisions, ownership classification, marker dedup, exit codes and
the single-comment-per-round contract are unchanged. No Makefile target, workflow or image
changes.

## Not covered

- The `AGENTS.md` §6s wording half of #1335 — a rulebook write that needs human sign-off
  under rule 3c. This headless leg declares the exact row as an owed row in `findings.md`
  instead of editing `AGENTS.md`.
- The other modes named in #1334 (`check`/`advance`/`adopt`): that is a reviewer ruling, not
  this change.
