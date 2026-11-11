# Tasks: fix-publish-latest-tag

- [x] `publish()` tags `latest_tag()` on the build, so the `:latest` push has a local tag
- [x] `tests/test_ensure_image.py`: the fake `docker` records tags and refuses to push an untagged ref (second alarm)
- [x] Falsified: the publish tests fail on the untagged-`:latest` code (3 fails) and pass on the fix
- [x] Tracked OpenSpec change `fix-publish-latest-tag` (proposal + spec + tasks)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make test`, `make architecture-check`, `make openspec-check`
- [x] Commit, push, open the PR with `closes #232`; qa-validate green on the PR
- [x] After merge: a real dispatch of `publish-agent-image` reaches the build and pushes both refs
