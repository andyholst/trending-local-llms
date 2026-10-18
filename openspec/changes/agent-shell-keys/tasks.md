# Tasks

- [x] 1. Write the proposal + spec for `bot-agent-run-safety` (issue #359).
- [x] 2. `Makefile`: ONE `AGENT_SHELL_KEYS` list; host-only export of `_HERMES_FORCE_<NAME>` from `<NAME>` (set keys only); `DOCKER_RUN` / `TEST_RUN` forward `$(AGENT_SHELL_FORWARD)` by name.
- [x] 3. `scripts/agent_shell_keys_check.py`: drive Hermes's real `LocalEnvironment` in the bot image; per-key lengths only; exit 1 on a blind key, exit 2 on a key missing from the container; `--allow-unconfigured` loud opt-out.
- [x] 4. `Makefile`: `_agent-shell-keys-check` / `agent-shell-keys-check` (in `DOCKER_RUN`), and `_search-preflight` runs it for `FIRECRAWL_API_KEY`.
- [x] 5. `qa-validate.yml` `live-smoke`: `make agent-shell-keys-check` with the real secrets.
- [x] 6. `tests/test_agent_shell_keys.py`: RED with plain names / GREEN with forced names against the real Hermes; by-name only (`make -n` sentinel); make's export; loud missing key; wiring. Verified RED against `origin/master`'s Makefile.
- [x] 7. `tests/test_agent_shell_keys.py` wired into `make test` (rule 6d).
- [x] 8. `AGENTS.md` §3e sentence + §8 row; `ARCHITECTURE.md` target, script, search and `live-smoke` rows; `OPENSPEC.md` index refreshed.
- [x] 9. `findings.md` written and `make findings-check` green (rule 6g).
- [x] 10. Gates green: `make lint`, `make check-secret-output`, `make secret-scan`, `make test`, `make architecture-check`, `make openspec-check`.
