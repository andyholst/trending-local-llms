# Tasks

- [x] 1. Write the proposal + `issue-implementer` capability spec for issue #522.
- [x] 2. `.github/workflows/issue-bot.yml`: `recheck` step (id) directly before the agent, after the checkout, with both exit-code contracts.
- [x] 3. `.github/workflows/issue-bot.yml`: gate `impl`, `verdict`, `salvage`, `Report the outcome` and the fail-loud step on `steps.recheck.outputs.closed != 'true'`.
- [x] 4. `tests/test_workflows.py`: ordering (before the agent, after the checkout), both contracts, both outputs, and every gated step.
- [x] 5. Verified RED against `origin/master`'s workflow (9 failures; master's only `issue-state` call is at step 19, after the agent at 7) and GREEN after (864 passed).
- [x] 6. `findings.md` written; `AGENTS.md` §8 row attempted (protected file — recorded if refused).
- [x] 7. `OPENSPEC.md` regenerated; `make lint`, `make openspec-check`, `make architecture-check` green.
