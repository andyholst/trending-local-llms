# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `baseline_info()` reads the baseline's `as_of` and measures its age against the analysis' as-of
- [x] 3. `render()` carries `- baseline: recorded <as_of> (N day(s) before this analysis)`
- [x] 4. The CLI always reports the baseline it compared against, and shouts STALE (with `make data-gap-baseline`) at `STALE_DAYS`
- [x] 5. The stale sentence is also a report finding, so the filed issue carries it
- [x] 6. `tests/test_data_gap_baseline_age.py` drives the real functions and the real CLI (stale, fresh, missing, unparseable)
- [x] 7. Verified RED on the pre-change script (6 failures) and GREEN after (`PASSED 15 | FAILED 0`)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
