# Tasks: fix-publish-ghcr-owner-pat

- [x] The login step sets `GHCR_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}`, passed by NAME (no `${{ }}` in the `run:` line)
- [x] The probe step sets `GITHUB_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}`
- [x] The `guard` job keeps `github.token` (it runs before any secret is read)
- [x] Tests assert the wiring: `test_publishing_uses_the_owner_pat_for_ghcr`, `test_the_probe_step_hands_over_the_token_the_script_reads`, and the guard test
- [x] `ARCHITECTURE.md`: the publish job's credential + the Tokens note (rule 6h)
- [x] Tracked OpenSpec change `fix-publish-ghcr-owner-pat` (proposal + spec + tasks)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make test`, `make architecture-check`, `make openspec-check`
- [x] Commit, push, open the PR with `closes #248`; qa-validate green on the PR
- [x] After merge: a forced dispatch of `publish-agent-image` reaches the build and pushes both refs
