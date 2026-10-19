# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `post_skip_note` walks EVERY fresh-verdict hold, bounded by `MAX_SKIP_NOTES`
- [x] 3. Each note carries its own `since=`, so idempotence stays per issue per round
- [x] 4. The run reports `N posted, M already noted (K held)` and what the bound left behind
- [x] 5. `test_the_skip_note_covers_every_held_issue` covers two holds, the same round twice, and eleven holds (the bound)
- [x] 6. Verified RED on the pre-change queue (5 failures, only #163 noted) and GREEN after (`PASSED 73 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
