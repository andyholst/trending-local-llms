# Tasks: pr-health-agent-login-1349

- [x] Add `AGENT_LOGINS` to `scripts/agent_identity.py` as the ONE definition of the agent GitHub login
- [x] Check the author login in `scripts/pr_health.py::is_bot_owned` (`is_bot` sufficient, not necessary)
- [x] Carry the live `is_bot: False` spelling in the fixture and add the RED-first login guard
- [~] Extend AGENTS.md §6s with the author-login contract and §8 with the row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Regenerate `OPENSPEC.md` and `ARCHITECTURE.md` §10
- [x] Run the focused module, `make lint`, `make architecture-check`, `make openspec-check` and `make test`
- [x] Write `findings.md` with the owed-row declaration and push the branch for review
