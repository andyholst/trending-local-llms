# Tasks

- [x] 1. Write the proposal + spec for the checkout-before-make invariant (issue #281).
- [x] 2. `issue-bot.yml`: the `Resolve the issue` step becomes decision-only (`gh`), so it needs no repository.
- [x] 3. `issue-bot.yml`: `make issue-thread` moves to its own step after `Checkout master`, before the reporter window, failing loudly on an empty `issue.md`.
- [x] 4. `tests/test_workflows.py::test_a_step_that_calls_make_runs_after_the_checkout` — the class guard, verified RED against `origin/master`'s `issue-bot.yml` (4 failures) and green here.
- [x] 5. `AGENTS.md` §8 guard row + §6e note that the resolver is repo-free (protected file — review-required, rule 3c).
- [x] 6. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan` green.
- [x] 7. Commit, push `issue-bot-checkout-first`, open the PR (`closes #281`).
- [x] 8. Monitor qa-validate to green and report the live confirmation (a real sweep reaching its PR step) on #281.
