# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `verdict_chain_start()` measures the hold from the OLDEST marker of the unbroken chain
- [x] 3. `VERDICT_MAX_HOLD_HOURS` (24 × 7) is the ceiling; past it the hold expires and the issue returns to the pick order
- [x] 4. The row and `render()` carry `verdict_held_since`, `verdict_held_hours`, `verdict_expired`; the log names an expiry loudly
- [x] 5. `--verdict-max-hold-hours` / `VERDICT_MAX_HOLD_HOURS` makes the ceiling injectable
- [x] 6. Tests cover a 200 h chain (expired), a 40 h chain (held, age reported) and a stale gap (chain broken)
- [x] 7. Verified RED on the pre-change queue (7 failures) and GREEN after (`PASSED 76 | FAILED 0`)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
