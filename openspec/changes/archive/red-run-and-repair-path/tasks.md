# Tasks

- [x] 1. Proposal + capability spec for `red-run-and-repair-path` (issue #558): run 40174402542 /
  PR #557, where a red loop reported success and no dispatch reached the PR.
- [x] 2. `issue-bot.yml`: "Fail when the implementation is not green" — red on
  `steps.loop.outputs.green == 'false'`, after the loop, naming the issue and the PR.
- [x] 3. `qa-validate.yml`: `dispatch-fixbot` admits `ci/data-gap-*` beside `ci/trending-refresh-*`,
  keeping `failure()`, `pull_request` and the same-repo-head requirement.
- [x] 4. `tests/test_workflows.py::test_a_red_fix_loop_reds_the_run_and_reaches_fix_bot` asserts both.
- [x] 5. Regression proved RED on the pre-change workflows (5 findings against
  `git show origin/master:.github/workflows/{issue-bot,qa-validate}.yml`), green with the fix (841/0).
- [x] 6. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 7. Gates green: `make lint`, `make openspec-check`, `make architecture-check`.
- [x] 8. Commit, push, open the PR (closes #558) — reviewable, never a draft.
