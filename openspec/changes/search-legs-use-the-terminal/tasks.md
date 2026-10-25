# Tasks

- [x] 1. Write the proposal + capability spec for `bot-agent-run-safety` (issue #362).
- [x] 2. `Makefile`: ONE `TOOL_ASK` definition (terminal only; `execute_code` / `web_extract` / `web_search` forbidden; `scripts/update_trending.py` as the in-process alternative) embedded by all four `_search-<backend>` prompts.
- [x] 3. `.hermes/skills/data-search/SKILL.md`: the same rule as a `Rules` bullet; the header names `${FIRECRAWL_API_KEY}`.
- [x] 4. `skills/gather-data.md` §1: the mirror is reached from the terminal via the Firecrawl scrape API, not `web_extract`; the header names `FIRECRAWL_API_KEY`.
- [x] 5. `tests/test_search_tool_pinning.py`: one definition, all four legs, no inviting prompt, the wording proved through `make -n`, both documents, the prompt budget, and the runner wiring.
- [x] 6. Verified RED against `origin/master`'s `Makefile` (the wording is absent there) and GREEN on this change.
- [x] 7. `AGENTS.md` §8 row for the guard (rule 6c); `OPENSPEC.md` index refreshed.
- [x] 8. `findings.md` written and `make findings-check` green (rule 6g).
- [x] 9. Gates green: `make lint` (includes `check-agent-skills`), `make _test` (the recipe `make test` wraps in the test image), `make _validate` + `make _validate-mapped` (the recipes `make validate` / `make validate-mapped` wrap), `make architecture-check`, `make openspec-index-check`, `make openspec-tasks-check`, `make check-secret-output`, `make findings-check`. The container-only half of `make openspec-check` (`openspec validate` through the CLI image) cannot run inside the bot container — recorded as its own finding (rule 6g).
