# Tasks

- [x] 1. Write the proposal + spec for the fix-bot window (issue #198), on the marker shape registered by #197.
- [x] 2. `.github/workflows/fix-bot.yml`: the `Announce the window on the PR` step between `Resolve PR` and `Checkout`, carrying `<!-- fix-bot-start: <ISO8601Z> run=<id> -->` + branch + run URL, with the default `github.token` and `issues: write`.
- [x] 3. Close the window on every path: `<!-- fix-bot-end: <ISO8601Z> run=<id> -->` at the top of the existing `always()` outcome comment.
- [x] 4. `scripts/bot_markers.py`: move `(fix-bot, start)` / `(fix-bot, end)` from `DECLARED_BY` to `WRITTEN`.
- [x] 5. `tests/test_workflows.py::test_fix_bot_announces_its_window` (order, marker, token, the stdin body, the `always()` close), registered in `main()`.
- [x] 6. `ARCHITECTURE.md`'s `fix` job row and `AGENTS.md`'s §6b fix-bot bullet + §8 guard row.
- [x] 7. Verified: the new test fails on the pre-change workflow (447 passed / 9 failed) and passes with it (456 passed / 0 failed); `make lint` and `make openspec-check` green.
