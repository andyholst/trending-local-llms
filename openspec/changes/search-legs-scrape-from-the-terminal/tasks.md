# Tasks

- [ ] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #362).
- [ ] 2. `Makefile`: ONE `SCRAPE_ASK` definition (terminal tool, never `execute_code`, naming the empty-Bearer 401); embedded in all four `_search-*` prompts.
- [ ] 3. `tests/test_search_key.py`: `test_every_leg_prompt_pins_the_tool_the_key_reaches` + `test_the_tool_pin_has_exactly_one_definition`, both in `main()` so `make test` runs them.
- [ ] 4. `AGENTS.md` §8: the `tests/test_search_key.py` row names the new guard.
- [ ] 5. `OPENSPEC.md` index refreshed; `make openspec-tasks-check` + `make openspec-index-check` green.
- [ ] 6. `findings.md` written and `make findings-check` green (rule 6g).
- [ ] 7. Gates green: `make lint`, `make validate`, `make validate-mapped`, `make test`, `make architecture-check`.
