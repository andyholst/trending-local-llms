# Tasks

- [x] 1. Write the proposal + spec for the qa-validate guard (issue #279).
- [x] 2. `qa-validate.yml`: add the `guard` job as the first job (owner / write+ collaborator / the bot, actor AND triggering actor) with the `pull_request`/`push` bypass and the reason it exists.
- [x] 3. `qa-validate.yml`: `validate` and `live-smoke` declare `needs: guard`.
- [x] 4. `tests/test_workflows.py`: `BOT_GUARDS` gains qa-validate, so the existing `test_guard_behaviour` proves its guard for every caller class.
- [x] 5. `tests/test_workflows.py`: `test_a_repo_event_run_is_admitted_by_its_guard` (non-vacuous) and `test_a_guarded_pipeline_gates_the_jobs_that_read_secrets` (guard first, guard job un-gated, a job needs it).
- [x] 6. `AGENTS.md` §6j names qa-validate and the repo-event rule; §8 rows added.
- [x] 7. `ARCHITECTURE.md`: the qa-validate table carries its `guard` row.
- [x] 8. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan` green.
- [x] 9. Commit, push `qa-validate-guard`, open the PR (`closes #279`).
- [x] 10. Monitor the PR's qa-validate run to green — the new `guard` job's first real execution — and report it on #279.
