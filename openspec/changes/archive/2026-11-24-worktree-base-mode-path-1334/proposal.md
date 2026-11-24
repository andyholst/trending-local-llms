# Proposal: worktree-base-mode-path-1334

Issue: #1334

## Why

`scripts/worktree_base.py`'s three modes that take NO target branch — `check`, `advance`
(both its fresh and its moved branch) and `adopt` — reported the base SHA and HEAD but never
named the working tree they read, while `_summary` (`new`/`resume`, `:247`) and `mode_resume`
(`:489`) already print `path=`. On a host carrying the owner clone plus N worktrees,
`head=<sha>` alone is ambiguous evidence, and the measured #1330 harm class was exactly a
seam run in the WRONG checkout answering `up-to-date`. The reviewer's ACCEPT ruling on #1334
(comment `7123282471`) scopes this to NAMING ONLY.

## What Changes

- `mode_check` prints one additive `path=<abs>` line: the checkout it verified.
- `mode_advance` prints `path=<abs>` on BOTH branches — the fresh no-op and the moved one
  (the latter runs `git reset --hard <tip>`, a destructive write to an unnamed directory).
- `mode_adopt` prints `path=<abs>` (it runs `checkout -B` plus stash push/pop on that tree).
- `tests/test_worktree_base.py` gains
  `test_check_advance_and_adopt_name_the_checkout_they_read`, pinning all four lines against
  a real git fixture, registered in the module's own call list.

## Impact

Additive output only. No make target, workflow, data format, contract, image or rulebook
change; the `path=` key is the one `_summary`/`mode_resume` already emit, so existing readers
keep working. The new test function is not yet named by §8 — that row is owed and declared in
`findings.md` (rule 3c: a headless leg cannot write the protected rulebook).

## Not covered

- No wrong-checkout REFUSAL in `check`/`advance` (they take no branch argument, so there is no
  named-branch mismatch to detect, unlike `rebase`); `adopt`'s `MAX_RESUME_AHEAD` bound stays.
- No new make target, no workflow wiring, no CI dispatch, no merge, no master push.
