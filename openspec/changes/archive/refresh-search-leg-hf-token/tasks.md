# Tasks

- [x] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #363).
- [x] 2. `.github/workflows/refresh-bot.yml`: `search` job env sets `HF_TOKEN` from the repository secret, with the reason stated.
- [x] 3. `Makefile`: `_search-preflight` proves `FIRECRAWL_API_KEY` AND `HF_TOKEN` in the agent's shell; the stale "the search job is given no HF_TOKEN" comment and the pre-flight comment corrected.
- [x] 4. `skills/gather-data.md` §5: the leg's shell carries `HF_TOKEN` for an authenticated HF lookup, by name, never printed.
- [x] 5. `tests/test_workflows.py`: guard requiring the search job to forward every credential its leg uses, and the pre-flight to prove them — verified RED against `origin/master`'s workflow.
- [x] 6. `tests/test_agent_shell_keys.py`: the pre-flight assertion requires both names.
- [x] 7. `AGENTS.md` §8 row + §4's local `make refresh` command; `ARCHITECTURE.md` search-target and `agent-shell-keys-check` rows; `OPENSPEC.md` index refreshed. **The AGENTS.md half is OWED**: that file is protected and the write approval did not return, so the exact row + §4 sentence are recorded in `findings.md` for an approver (rule 3c). `ARCHITECTURE.md` and `OPENSPEC.md` are done.
- [x] 8. `findings.md` written and `make findings-check` green (rule 6g).
- [x] 9. Gates green: `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`.
