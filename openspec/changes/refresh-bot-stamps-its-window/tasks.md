# Tasks

- [x] 1. Write the proposal + spec for the refresh window (issue #199), on the marker shape registered by #197.
- [x] 2. `scripts/refresh_run_block.py`: the pure `render`, the API-reading `fetch`, and `current_block()` (which both surfaces embed).
- [x] 3. `make refresh-run-block` (host-run, like `data-gap-issue`: `gh` lives on the runner).
- [x] 4. `refresh-bot.yml`'s `aggregate` PR step composes the block into the PR body (inside the data-changed branch only).
- [x] 5. `scripts/data_gap_analysis.py` puts the same block at the top of the gap issue body.
- [x] 6. `scripts/bot_markers.py`: `(refresh-bot, run)` moves from `DECLARED_BY` to `WRITTEN`.
- [x] 7. `tests/test_refresh_run_block.py` (a real capture renders the expected block, legs by name, a loud failed read, the PR-path-only wiring, the gap-issue surface), registered in `main()` and wired into `make _test`.
- [x] 8. `AGENTS.md` §6b + §8 row; `ARCHITECTURE.md` target / `aggregate` / script rows.
- [x] 9. Verified: the guard fails on the pre-change tree (6 FAILs) and passes with it (20/0); `make lint` OK, `make architecture-check` OK, `make openspec-check` green.
