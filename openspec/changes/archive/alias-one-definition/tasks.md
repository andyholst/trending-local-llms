# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. All 8 `hermes -z` call sites pass `-m $(HERMES_ALIAS)` instead of the literal
- [x] 3. `MODEL_FLAG` / `_defined_alias()` replace the literals in the test suite (5 assertions, in `test_hermes_prompts.py` and `test_workflows.py`)
- [x] 4. `test_the_alias_has_exactly_one_definition` proves the single definition, the call sites, and the `make -n` expansion
- [x] 5. The two vacuity checks count the variable form (they cannot pass by matching nothing)
- [x] 6. Verified RED against the pre-change `Makefile` (4 failures) and GREEN after (`PASSED 81 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test` (59 modules), `make architecture-check` and `make openspec-check` green
