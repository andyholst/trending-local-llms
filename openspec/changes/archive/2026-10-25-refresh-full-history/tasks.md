# Tasks

- [x] 1. Proposal + capability spec for `refresh-full-history` (issue #552): the measured
  `[qa-report] make test reported findings (rc=2)` on a `is-shallow-repository=true` checkout.
- [x] 2. `refresh-bot.yml`: the `aggregate` checkout asks for `fetch-depth: 0`, with the measured
  failure and why the aggregate's advisory QA pass depends on it.
- [x] 3. `tests/test_workflows.py`: `test_a_job_that_runs_the_suite_checks_out_the_whole_history`
  guards every job that runs `make test`/`qa-report`/`check-commit-authorship`, ignoring mentions
  inside shell comments; registered in the module's `main()`.
- [x] 4. Regression proved RED on the pre-change workflow: the guard fails
  `refresh-bot.yml aggregate: the checkout is the full history` against
  `git show origin/master:.github/workflows/refresh-bot.yml`, and passes with the fix.
- [x] 5. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 6. Gates green: `make lint`, `make openspec-check`, `make architecture-check`, and
  `tests/test_workflows.py` in the test image.
- [x] 7. Commit, push, open the PR (closes #552) — reviewable, never a draft.
