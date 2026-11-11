# Tasks

- [x] 1. Write the proposal + capability spec for `pr-body-composition` (issue #287).
- [x] 2. `scripts/pr_body.py`: `render()` / `closing_line()` / `main(--issue --branch)`, importing `pr_closure.implemented_issue()` and REFUSING a branch that encodes another issue (exit 2, empty stdout).
- [x] 3. `Makefile`: `make pr-body ISSUE=<n> [BRANCH=<branch>]`, `@`-silenced so no recipe line reaches the body.
- [x] 4. `.github/workflows/issue-bot.yml`: the "Open the PR" step composes the body with `make --no-print-directory pr-body … > pr-body.md` and hands it to `gh pr create --body-file`; no heredoc, no `printf`.
- [x] 5. `tests/test_pr_body.py`: composer, make recipe and the SHIPPED step executed (stub `gh` only), the body fed to `scripts/pr_closure.py`, plus the branch-mismatch refusal and the usage error.
- [x] 6. `tests/test_workflows.py`: `_run_issue_pr_step()` executes the step in the checkout so the real recipe runs; `pr-body.md` cleaned up.
- [x] 7. Regression proved on the pre-change tree: the new test's workflow assertions FAIL against `git show origin/master:.github/workflows/issue-bot.yml`.
- [x] 8. `ARCHITECTURE.md`: the `pr-body` target row, the `scripts/pr_body.py` row, and the regenerated §10 (`make architecture-refresh`).
- [x] 9. `AGENTS.md` §8 row, and the `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 10. Gates green: `make validate`, `make validate-mapped`, `make test`, `make openspec-check`, `make architecture-check`.
- [x] 11. Commit, push, open the PR (`closes #287`) — reviewable, never a draft, never merged here.
