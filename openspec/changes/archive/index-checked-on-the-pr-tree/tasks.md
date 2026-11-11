# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. The validate job checks out the PR head (falling back to github.sha)
- [x] 3. Full history is kept (the authorship guard needs the base ref)
- [x] 4. The push run still verifies master's own index
- [x] 5. Guard added for the ref expression and fetch-depth
- [x] 6. Reproduced from two real red runs (#429, #430) with the same wording
- [x] 7. `OPENSPEC.md` regenerated; `openspec-check` green
- [x] 8. `make lint` and `make test` green
