# Tasks

- [x] 1. Write the proposal + spec for the one-bot-at-a-time verification protocol.
- [x] 2. `AGENTS.md` §6b: add the **Bot verification protocol — one bot at a time** block (order, fix-PR-with-guard contract, green-gate before the next bot, `auto-merge`-only merge, post-merge verification pass).
- [x] 3. `tests/test_workflows.py::test_bot_verification_protocol_is_documented_and_guarded` — the protocol's wording guard, plus re-proof that the guard is the FIRST step of its job in every pipeline `BOT_GUARDS` names.
- [x] 4. Register the test in `tests/test_workflows.py`'s `main()`.
- [x] 5. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan` green.
- [x] 6. Commit, push, open the PR.
