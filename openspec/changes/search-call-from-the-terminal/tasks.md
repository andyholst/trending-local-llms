# Tasks

- [ ] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #362).
- [ ] 2. `Makefile`: ONE `TOOL_ASK` block; embed it in all four `_search-*` prompts.
- [ ] 3. `skills/gather-data.md` + `.hermes/skills/data-search/SKILL.md`: the same tool pin.
- [ ] 4. `tests/test_search_key.py`: lock the wording — one definition, terminal named,
      `execute_code` refused with the reason, documents in agreement.
- [ ] 5. Prove the guard RED against `origin/master`'s Makefile (rule 6c).
- [ ] 6. `AGENTS.md` §3e sentence + §8 row for the guard.
- [ ] 7. `OPENSPEC.md` index refreshed (`make openspec-index`), `make openspec-tasks-check` green.
- [ ] 8. `findings.md` written and `make findings-check` green (rule 6g).
- [ ] 9. Gates run: `make test`, `make validate`, `make validate-mapped`, `make openspec-check`,
      `make architecture-check` (docker-dependent stages reported honestly).
