# Tasks

- [x] 1. Write the proposal + `architecture-description` capability spec for issue #544.
- [x] 2. `scripts/architecture_bot.py`: `command_text()` drops heredoc bodies and quoted strings before the `make` sweep.
- [x] 3. `tests/test_architecture_bot.py`: prose is not a call; a real call with a quoted argument still is; qa-validate's real targets survive.
- [x] 4. Verified RED against `origin/master`'s `architecture_bot.py` (3 failures, both phantom targets reported) and GREEN after (72 passed).
- [x] 5. `make architecture-refresh` + `make architecture-check` green; the generated §10 block is unchanged on this tree.
- [x] 6. `AGENTS.md` §8 guard row (rule 6c, review-required rule 3c); `findings.md` written.
- [x] 7. `OPENSPEC.md` regenerated; `make lint`, `make openspec-check`, `make findings-check` green.
