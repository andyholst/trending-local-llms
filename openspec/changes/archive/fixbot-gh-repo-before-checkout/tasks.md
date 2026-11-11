# Tasks

- [x] 1. Write the proposal + capability spec for issue #331 (`fixbot-before-checkout`: a job that calls `gh` before its checkout names the repo, and the guard that proves it).
- [x] 2. `.github/workflows/fix-bot.yml` — `GH_REPO: ${{ github.repository }}` in the `fix` job's env, covering the window announcement, the PR resolution and the early-death result comment.
- [x] 3. `tests/test_workflows.py` — `test_gh_before_the_checkout_names_the_repo`: scan every workflow/job for an implicit `gh` subcommand before the checkout, and pin `fix-bot.yml`'s `fix` job by name so the guard cannot go vacuous.
- [x] 4. Proved the guard FAILS on `git show origin/master:.github/workflows/fix-bot.yml` (`FAILED 2`) and passes on the fixed tree (`FAILED 0`).
- [x] 5. Verified: `make test`, `make lint`, `make openspec-check`, `make architecture-check` green.
- [x] 6. `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 7. PR #330's red link repaired in its own commit (the repo id corrected in the raw snapshot and the store, README regenerated, `make validate` PASSED) so the queued refresh can land.
