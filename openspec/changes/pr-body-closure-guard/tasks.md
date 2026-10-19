# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `_run_issue_pr_step()` executes the REAL "Open the PR" step with a stub `gh` and captures its `--body-file`
- [x] 3. The body is checked with `scripts/pr_closure.py` (`check()` and `closing_bindings()`), not with a marker-word search
- [x] 4. The marker-word assertion is deleted
- [x] 5. The test refuses the two measured shapes (`closes #271 and #276`, `closes #999`), proving it is not vacuous
- [x] 6. Verified RED by mutating the workflow's closing line to `Closes #%s and #999` (2 failures, `[(376, [376, 999])]`) and GREEN when reverted
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
