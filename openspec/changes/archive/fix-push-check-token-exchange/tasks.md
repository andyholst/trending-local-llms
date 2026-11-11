# Tasks: fix-push-check-token-exchange

- [x] `push_check()` exchanges the ambient token for a push-scoped GHCR token (Basic auth → `/token` → `Bearer`)
- [x] `_docker_user()` reads the login's username from the docker config (non-empty, GHCR ignores it)
- [x] `tests/test_publish_agent_image.py`: the fake registry serves the token endpoint and asserts the SCOPED token on the upload
- [x] Tracked OpenSpec change `fix-push-check-token-exchange` (proposal + spec + tasks)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make test`, `make architecture-check`, `make openspec-check`
- [x] Commit, push, open the PR with `closes #232`; qa-validate green on the PR
