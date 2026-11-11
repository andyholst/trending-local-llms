# Tasks

- [x] 1. The tracked change exists (this directory) before the test edit
- [x] 2. The test reads the `id: drift` and commit/push/PR steps OUT of the workflow with PyYAML
- [x] 3. It executes both in a temp repo with a real bare remote, the repo's own `make git-identity`, and a stub `gh` on `PATH`
- [x] 4. No-op half asserted: `changed=false`, no branch, `gh` never called
- [x] 5. Drift half asserted: `changed=true`, one `ci/architecture-<UTC>Z` branch, canonical author, `pr create --base master --body-file -`, run URL in the body, no closing keyword
- [x] 6. The branch name is judged by `scripts/pr_closure.py`'s own regexes, not a re-spelled rule
- [x] 7. The three string assertions it subsumes are removed
- [x] 8. Proven to bite: dropping the `Z` stamp fails the branch check; adding `Closes #479` to the body fails the keyword check; both restored green
- [x] 9. Gates: `make test` (58 checks in this module), `make lint`, `make architecture-check`, `make openspec-check`, `make validate-mapped`
- [x] 10. `OPENSPEC.md` regenerated; `findings.md` written (`- none` — the finding was this issue)
