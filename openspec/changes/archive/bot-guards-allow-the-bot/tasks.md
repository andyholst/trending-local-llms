# Tasks

- [x] 1. Write the proposal + spec for the guard contract (issue #238).
- [x] 2. Add the `github-actions[bot]` allowance to every bot guard (`refresh-bot`, `fix-bot`, `issue-bot`, `issue-review-bot`, `publish-agent-image`).
- [x] 3. Add the `schedule` bypass to `issue-bot` and `issue-review-bot` so the cron path is uniform.
- [x] 4. Extend `tests/test_workflows.py`: the bot actor is ALLOWED by every bot guard; read/triage and non-collaborators stay REFUSED; every bot guard with a cron has the schedule bypass.
- [x] 5. `AGENTS.md` rule 6j adds the bot identity (protected file — review-required, rule 3c).
- [x] 6. Update `ARCHITECTURE.md`'s guard rows; run `make test`, `make architecture-check`, `make openspec-check`.
- [x] 7. Commit, push, open the PR (closes #238); qa-validate auto-merges when green.
