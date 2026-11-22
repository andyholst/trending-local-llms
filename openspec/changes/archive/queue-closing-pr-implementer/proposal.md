# Proposal: queue-closing-pr-implementer

Issue: #1310
PR: #1313

## Why

`scripts/issue_queue.py::build` decides "has this issue an implementer?" from a
`ci/data-gap-<n>-*` branch, or from an open PR whose `headRefName` IS that branch. But
agent-owned PRs are cut as `fix/…`, `feat/…` and `rule/…`, so a prefix-only predicate is
blind to them. Measured live 2026-11-22: `make issue-queue` printed
`issue=1176 position=2 has_implementer=0 reason=next-sweep` while open PR #1289
(`fix/pr-block-grace-derived-1176`, head `ec8951c3`) carries one `closes #1176` binding —
the shared queue offered already-implemented work as the next sweep's pick, and a second
implementer could duplicate it. #1295 fixed this class for the rebase sweep; the
implementer's own queue has the same blind spot.

## What Changes

- `scripts/issue_queue.py` reads each open PR's `body` beside its branch and marks an
  issue as having an implementer when ANY open PR's body binds a closing keyword to that
  issue number — parsed through `scripts/pr_closure.py`'s ONE closure parser (rule 6d),
  never a second copy of the keyword list.
- The prefixed-branch path is unchanged, and the closing PR also supplies the PR activity
  timestamps (`createdAt`/`updatedAt`) for `last_implementer_activity`.
- `tests/test_issue_review.py` gains a guard that fails on the base script where a
  `fix/`-prefixed closing PR is wrongly offered as `next-sweep`.

## Impact

One script, one test module. No workflow, make target, data format or contract change.
An issue with an open closing PR is no longer re-offered to the implementer sweep, so a
reviewer's in-flight work is not duplicated.

## Not covered

- The reviewer's `REVIEW_GAP_HOURS` window and the `issue-queue` label union (unchanged).
- Merged or closed PRs: only an OPEN PR marks an implementer here, as before.
