# Tasks

- [x] 1. Write the proposal + spec for the issue-write token rule and the label-first filing (issue #277).
- [x] 2. `refresh-bot.yml`: the `aggregate` job declares `permissions: issues: write` and `make data-gap-issue` runs with the default token.
- [x] 3. `code-review-bot.yml`: its issue-filing step moves to the default token (the same class).
- [x] 4. `scripts/data_gap_analysis.py`: create `data-gap-analysis` when the repo lacks it; quote `gh`'s own stderr on both failure paths.
- [x] 5. `tests/test_workflows.py::test_issue_writes_use_the_default_token` — the class guard over every workflow.
- [x] 6. `tests/test_data_gap_analysis.py` — label-first creation, gh's message on the loud paths, and the corrected token assertion.
- [x] 7. `make test` green in the test image.
- [x] 8. `AGENTS.md` §4 data-gap bullet + §6b token paragraph name the token and the label rule (protected file — review-required, rule 3c).
- [x] 9. `make openspec-check`, `make architecture-check`, `make secret-scan` green.
- [x] 10. Commit, push `data-gap-filer-token`, open the PR (`closes #277`).
- [x] 11. Monitor the PR's qa-validate run until every check is green; report the live confirmation (the next refresh-bot filing carries the label) on #277.
