# Tasks

- [x] 1. The tracked change exists (this directory) before the code edit
- [x] 2. `scripts/check_makefile_knobs.py` — use-shape readers, prose/fixture/archive exclusion, exit 0/1/2
- [x] 3. `HERMES_LOG_TAIL` removed from the `Makefile`, seam comment states the real bound
- [x] 4. `make check-makefile-knobs` public target bundled into the `lint` recipe (rule 6d)
- [x] 5. `tests/test_makefile_knobs.py` — planted dead knob red, prose-only red, use shapes green, missing Makefile exit 2, real Makefile green, dead knob gone, lint wiring
- [x] 6. `tests/test_scrub_log.py` fixtures drop their stale `HERMES_LOG_TAIL` copy
- [x] 7. `ARCHITECTURE.md` rows (lint target table, §6 scripts table) + `AGENTS.md` §8 guard row + `make architecture-refresh`
- [x] 8. `make lint`, `make architecture-check`, `make architecture-refresh` green locally; `make openspec-check` green on this state
- [x] 9. PR opened from this branch (CI watched green in the run window); `findings.md` written
