# Tasks

- [x] 1. Write the proposal + spec for the rule 6j guard placement (issue #259).
- [x] 2. `.github/workflows/fix-bot.yml`: the guard becomes its own FIRST job with no secret; the work moves to a `fix` job with `needs: [guard]` holding the four secrets at job level.
- [x] 3. `tests/test_workflows.py`: `BOT_GUARDS` points fix-bot at its `guard` job and gains `code-review-bot.yml` + `queued-alarm.yml` (both carried guards nothing executed).
- [x] 4. `tests/test_workflows.py::test_guard_is_before_any_secret` — the guard job declares no secret, no guard step touches one, the guard needs nothing, every sibling job needs it — registered in `main()`.
- [x] 5. `tests/test_workflows.py::test_owner_guards` asserts the fix-bot shape directly.
- [x] 6. Verified RED on `origin/master`'s `fix-bot.yml` (6 named failures) and green with it (608 checks, 0 failures).
- [x] 7. `ARCHITECTURE.md`: fix-bot's `guard` job row and `needs: [guard]` on `fix`.
- [x] 8. `findings.md`: the owed `AGENTS.md` row AND the hand-maintained `BOT_GUARDS` registry (rule 6g) — neither fixed here.
- [x] 9. `make openspec-check`, `make lint`, `make architecture-check`, `make findings-check` green.
- [x] 10. Commit, push, open the PR (ready for review, never a draft).

> The `AGENTS.md` §8 row rule 6c asks for is **not a task of this change**: `AGENTS.md` is a
> protected rule file whose write approval has not returned, so the row cannot be authored here.
> It is recorded in `findings.md` and filed as its own issue (#212's situation) rather than ticked
> off untruthfully or worked around.
