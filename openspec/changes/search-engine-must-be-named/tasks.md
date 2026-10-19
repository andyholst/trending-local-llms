# Tasks

- [x] 1. The tracked change exists (this directory) before any edit
- [x] 2. `Makefile` gains ONE `ENGINE_ASK` definition; all four legs expand `$(ENGINE_ASK)` and carry no second copy
- [x] 3. `ENGINE_ASK` requires the engine the post ACTUALLY NAMES, states a model/vendor/quantization is NEVER an engine (naming the measured tokens), and says a post naming no engine means SKIP that measurement because a t/s with no engine is not a valid entry
- [x] 4. `ENGINE_ASK` keeps every rule the inline copies carried (registered names, fork name, `engine_repo`, one verified web search, never an invented URL)
- [x] 5. `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_engine_rule_from_one_definition` locks it, and the guard was proved RED against the pre-change `Makefile` (18 FAIL) and GREEN after (71 passed, 0 failed)
- [x] 5b. `tests/test_engine_aliases.py::test_prompts_mention_forks` follows the same one-definition shape (the fork sentence is checked once in `ENGINE_ASK`, every leg is checked to expand it), so the extraction does not silently drop the fork rule (rule 6b)
- [x] 6. `make -n _search-<leg>` still yields exactly one masked `hermes -z` command per leg (`tests/test_hermes_prompts.py::test_make_dry_run_single_hermes_command`)
- [x] 7. `findings.md` records the `AGENTS.md` §8 row this run cannot write (protected file) and the refresh aggregate's whole-refresh abort
- [x] 8. No `data/**` file changes; `README.md` untouched
- [x] 9. `OPENSPEC.md` regenerated; `make openspec-check`, `make architecture-check`, `make lint`, `make validate-search`, `make test` green
