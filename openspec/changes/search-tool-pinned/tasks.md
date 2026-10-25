# Tasks

- [ ] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #362).
- [ ] 2. `Makefile`: one `SEARCH_TOOL_ASK` definition (terminal tool, `execute_code` forbidden by name, the empty-Bearer / `HTTP 401` reason, no double quote), taken by all four `_search-*` prompts as `$(SEARCH_TOOL_ASK)`.
- [ ] 3. `.hermes/skills/data-search/SKILL.md`: the leg's own skill pins the same tool.
- [ ] 4. `skills/gather-data.md` §1: the scrape is made from the terminal tool, never `execute_code`, and why.
- [ ] 5. `tests/test_search_key.py`: `test_the_prompts_pin_the_tool_that_can_see_the_key` (one definition, its content, every leg takes it, no inline copy, no double quote) and `test_the_skill_the_leg_preloads_pins_the_same_tool`; both wired into `main()`.
- [ ] 6. `AGENTS.md` rule 3e paragraph + §8 row for the new guard.
- [ ] 7. `findings.md` written and `make findings-check` green (rule 6g).
- [ ] 8. `OPENSPEC.md` index refreshed; `make openspec-tasks-check` + `make openspec-index-check` green.
- [ ] 9. Gates green on the host shapes available here: `make _validate`, `make _validate-mapped`, `make _test`, `make architecture-check`, `make lint`.
- [ ] 10. Commit, push, open the PR (`closes #362`) — reviewable, never a draft, never merged here.
