# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `hermes-alias-check` runs `make _setup 1>&2` instead of `>/dev/null`
- [x] 3. `hermes-smoke` runs `make _setup 1>&2` instead of `>/dev/null`
- [x] 4. `test_no_wrapper_discards_the_seams_diagnosis` scans the real Makefile (non-vacuous, per-target assertions)
- [x] 5. Verified RED against the pre-change `Makefile` (4 failures naming both lines) and GREEN after (`PASSED 60 | FAILED 0`)
- [x] 6. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 7. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
