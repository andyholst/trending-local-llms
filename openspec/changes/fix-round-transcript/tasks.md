# Tasks

- [x] 1. Proposal + capability spec for `fix-round-transcript` (issue #566).
- [x] 2. `fix-bot.yml`: the QA artifact carries `hermes-run.scrubbed.log` beside `qa-report.txt`,
  with the measured run and why the raw capture is never uploaded.
- [x] 3. `tests/test_workflows.py::test_a_detached_fix_round_leaves_its_transcript_behind` asserts
  both halves and is registered in the module's `main()`.
- [x] 4. Regression proved RED on the pre-change workflow (the scrubbed-log assertion fails against
  `git show origin/master:.github/workflows/fix-bot.yml`).
- [x] 5. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 6. Gates green: `make lint`, `make openspec-check`, `make architecture-check`, `test_workflows`.
- [x] 7. Commit, push, open the PR (closes #566) — reviewable, never a draft.
