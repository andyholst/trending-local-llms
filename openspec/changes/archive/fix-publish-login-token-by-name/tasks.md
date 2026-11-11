# Tasks: fix-publish-login-token-by-name

- [x] The login step passes `GHCR_TOKEN` / `GHCR_USER` through `env:`; the `run:` line interpolates no `${{ }}`
- [x] `test_publishing_uses_the_default_token_not_a_pat` asserts the token is passed by NAME and the run line carries no `${{ }}`
- [x] Tracked OpenSpec change `fix-publish-login-token-by-name` (proposal + spec + tasks)
- [x] Finding filed: the guard does not flag `${{ github.token }}` in a run block (#241)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make test`, `make architecture-check`, `make openspec-check`
- [x] Commit, push, open the PR with `closes #240`; qa-validate green on the PR
