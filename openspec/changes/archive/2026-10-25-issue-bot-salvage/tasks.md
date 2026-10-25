# Tasks

- [x] 1. Proposal + capability spec for `issue-bot-salvage` (issue #554): the measured run 40168796244,
  where a detached run's finished change was discarded.
- [x] 2. `issue-bot.yml`: the "Did the agent leave work behind?" step reads `git status --porcelain`
  (gitignored scratch is invisible to it) and reports `dirty`.
- [x] 3. `issue-bot.yml`: the commit/push step runs on `implemented == 'true'` **or** `dirty == 'true'`;
  "Fail loudly" requires `dirty != 'true'`.
- [x] 4. `tests/test_workflows.py::test_issue_bot_salvages_a_detached_runs_work` reads the shipped step
  and EXECUTES its `run:` text in a real git repo, clean and dirty, and checks the two conditions.
- [x] 5. Regression proved RED on the pre-change workflow: three assertions fail against
  `git show origin/master:.github/workflows/issue-bot.yml`.
- [x] 6. `tests/test_workflows.py` green in the test image (833 passed, 0 failed).
- [x] 7. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 8. Gates green: `make lint`, `make openspec-check`, `make architecture-check`.
- [x] 9. Commit, push, open the PR (closes #554) — reviewable, never a draft.
