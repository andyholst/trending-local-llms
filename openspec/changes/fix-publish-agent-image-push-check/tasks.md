# Tasks: fix-publish-agent-image-push-check

- [x] Add `env: GITHUB_TOKEN: ${{ github.token }}` to the workflow's probe step
- [x] Add `tests/test_publish_agent_image.py::test_the_probe_step_hands_over_the_token_the_script_reads` and register it in `main()`
- [x] Tracked OpenSpec change `fix-publish-agent-image-push-check` (proposal + spec + tasks)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make test`, `make architecture-check`, `make openspec-check`
- [x] Commit, push, open the PR with `closes #229`; qa-validate green on the PR
