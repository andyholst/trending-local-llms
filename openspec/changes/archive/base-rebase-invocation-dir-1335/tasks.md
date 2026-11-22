# Tasks: base-rebase-invocation-dir-1335

- [x] Name the branch worktree as the `make base-rebase` invocation dir in `scripts/pr_health.py::rebase_comment_body`
- [x] Assert the posted remedy names that worktree in `tests/test_pr_health.py`
- [x] Prove the guard RED on the base revision of `scripts/pr_health.py`
- [x] Run the module, `make lint`, `make architecture-check` and `make test`
- [x] Write `findings.md` with the owed rule-3c row, regenerate `OPENSPEC.md`, run `make openspec-check`
- [~] AGENTS.md §6s wording names the branch worktree as the invocation dir — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); exact row text in `findings.md`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks
