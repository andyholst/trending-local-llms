# Tasks

- [x] 1. The pinned model is read from the endpoint and the dated + floating ids are compared
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `Makefile`: `HERMES_MODEL` -> `deepseek/deepseek-v4.1-flash-1017`
- [x] 4. `AGENTS.md` §4 rule (dated snapshot, never the alias) + §6 prose
- [x] 5. `skills/gather-data.md` + `refresh-bot.yml` PR-body prose name the new pin
- [x] 6. `tests/test_search_budget.py` refuses a floating-alias pin (RED on the old value)
- [x] 7. `tests/test_install_hermes_ci.py` stub answers the new pin (rule 6b)
- [x] 8. `make test`, `make lint`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 9. `findings.md` written (rule 6g)
