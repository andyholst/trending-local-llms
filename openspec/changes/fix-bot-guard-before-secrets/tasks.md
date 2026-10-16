# Tasks

- [x] 1. Write the proposal + spec for the rule 6j guard placement (issue #259).
- [x] 2. `.github/workflows/fix-bot.yml`: the guard becomes its own FIRST job with no secret; the work moves to a `fix` job with `needs: [guard]` holding the four secrets at job level.
- [x] 3. `tests/test_workflows.py`: `BOT_GUARDS` points fix-bot at its `guard` job and gains `code-review-bot.yml` + `queued-alarm.yml`.
- [x] 4. `tests/test_workflows.py::test_guard_is_before_any_secret` (guard job holds no secret, no guard step touches one, the guard needs nothing, every other job needs it), registered in `main()`.
- [x] 5. `tests/test_workflows.py::test_owner_guards` asserts the fix-bot shape directly.
- [x] 6. Verified RED on the pre-change workflow (3 named failures against `origin/master`'s `fix-bot.yml`) and green with it (539 checks, 0 failures, whole `test_workflows.py`).
- [x] 7. `AGENTS.md` §6j (the enforceable form of the rule) + §8 guard row.
- [x] 8. `ARCHITECTURE.md`: fix-bot's `guard` job row and `needs: [guard]` on `fix`.
- [x] 9. `make openspec-check`, `make lint`, `make architecture-check`, `make test` green.
- [x] 10. File the findings (`make findings-check` + `make file-findings`) and run `make secret-scan`.
- [x] 11. Commit, push, open the PR (ready for review, never a draft).
