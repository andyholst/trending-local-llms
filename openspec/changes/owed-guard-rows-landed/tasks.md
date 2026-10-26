# Tasks

- [x] 1. Write the proposal + `agents-guard-registry` capability spec for the owed-row ledger.
- [x] 2. `AGENTS.md` §8: ten rows applied from each change's `findings.md` ledger (guards named, failures described, issues cited).
- [x] 3. `AGENTS.md` §6j: `issue-bot-already-fixed` added to the `issue-bot` row.
- [x] 4. `scripts/bot_markers.py`: the marker registered (`issue-bot`/`already_fixed`) and in `WRITTEN`; `UNREGISTERED_OWED` emptied.
- [x] 5. `tests/test_agents_rows.py::test_the_rows_this_session_owed_are_written` pins all ten rows plus the registration.
- [x] 6. `tests/test_bot_markers.py`: the owed-list check allows an empty list (it may only shrink).
- [x] 7. Verified: `test_agents_rows` 24/24, `test_bot_markers` 57/57.
- [x] 8. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
