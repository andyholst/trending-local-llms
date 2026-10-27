# Tasks

- [x] 1. Write the proposal + spec for `agent-leg-skills` (issue #638).
- [x] 2. `.hermes/skills/data-search/SKILL.md`: absorb the engine rule, the five dimensions, the terminal-tool pin, the post-signal rule, the per-query write and the AMD/ROCm rules; document each backend's parameters.
- [x] 3. `Makefile`: delete `DIM_ASK`, `ENGINE_ASK` and `SCRAPE_ASK`; make the four `_search-*` recipes pointers plus parameters (`backend`, keywords, `$(MODEL_QUERIES)`, `--write-raw`).
- [x] 4. `Makefile`: trim `_fix`, `_implement-issue`, `_review-issue` and `_review-issue-window` to pointers plus their parameters.
- [x] 5. `scripts/check_agent_skills.py`: `PROMPT_BUDGET` 3200 → 900 and `RETIRED_RULES` (stated in the skill, absent from every recipe).
- [x] 6. Migrate the tests that pinned the rules in the Makefile: `test_hermes_prompts`, `test_search_key`, `test_post_signal`, `test_amd_backend`, `test_engine_registry`, `test_engine_aliases`, `test_search_budget`; extend `test_agent_skills` with the two new findings.
- [x] 7. `AGENTS.md`: §2 rule 6p + its §8 row, and correct the three §8 rows that still described the retired variables.
- [x] 8. `ARCHITECTURE.md`: the seam section and the `check-agent-skills` rows (budget 900, retired rules, the parameters a recipe carries).
- [x] 9. `OPENSPEC.md` index refreshed; `make openspec-check` green.
- [x] 10. Gates green: `make lint`, `make test`, `make validate`, `make architecture-check`, `make openspec-check`.
- [x] 11. Commit, push, open the PR (`closes #638`) — reviewable, never a draft, never merged here.
