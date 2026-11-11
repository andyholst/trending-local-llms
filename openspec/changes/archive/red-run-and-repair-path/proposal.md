# Proposal — red run and repair path

Issue: #558

## Why

Two halves of one gap, measured on run 40174402542 / PR #557 (the first implementation the repaired
sweep produced):

1. **The run lied.** The fix loop printed `[fix-loop] still RED after N round(s)` — it had caught
   `[openspec-tasks] FAIL search-call-from-the-terminal: unchecked task checkbox(es)` and given up
   after its rounds — and the job still reported `Fix loop against the PR branch: completed/success`.
   The step captures the loop's exit code into `green=false` and exits 0 so the outcome comment can
   post, and **nothing acted on that value**.
2. **Nothing could repair it.** `qa-validate`'s `dispatch-fixbot` fires only for
   `startsWith(github.head_ref, 'ci/trending-refresh-')`, so an implementer's PR
   (`ci/data-gap-<n>-…`) is never handed to fix-bot.

Together they make a red implementation look finished: the queue sees a branch, the PR sits open and
unmergeable, and the issue stays open until a human notices.

## What changes

- `issue-bot.yml` gains **"Fail when the implementation is not green"**: red when
  `steps.loop.outputs.green == 'false'`, naming the issue and the PR, so the run page agrees with the
  outcome comment it already posted.
- `qa-validate.yml`'s `dispatch-fixbot` condition admits `ci/data-gap-*` as well as
  `ci/trending-refresh-*`, keeping the same-repo-head and `failure()` requirements and the existing
  two-`fix-bot:`-commit cap.

## Impact

- `.github/workflows/issue-bot.yml`, `.github/workflows/qa-validate.yml` — one step and one condition.
- `tests/test_workflows.py::test_a_red_fix_loop_reds_the_run_and_reaches_fix_bot` — asserts the step,
  its condition, its `exit 1`, its position after the loop, and both branch families in the dispatch
  condition.
- No target, script, job or image changes, so `ARCHITECTURE.md` is unchanged.

## What is NOT covered

- The loop's round budget stays at 3: a change that needs more is a human's call, and now says so in
  red rather than in green.
- The red-run step does not comment on the PR — the outcome comment on the issue and the fix-bot
  path already carry the failure.
