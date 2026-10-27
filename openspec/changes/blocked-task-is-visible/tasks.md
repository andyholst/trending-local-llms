# Tasks

- [x] 1. The gap is reproduced against this tree (`- [~]` silently read as "all tasks checked")
- [x] 2. `scripts/check_openspec_tasks.py`: the blocked state, the annotation rule and the review-required report
- [x] 3. `tests/test_check_openspec_tasks.py`: blocked passes + is reported, blocked counts as unfinished, unannotated blocked fails, the Makefile words
- [x] 4. `scripts/openspec_index.py`: a blocked box counted as blocked, a blocked-free row unchanged
- [x] 5. `tests/test_openspec_index.py`: the `1/2 · 1 blocked` row
- [x] 6. `Makefile`: `openspec-check` echo and the `openspec-tasks-check` help text
- [x] 7. `ARCHITECTURE.md`: the target row and the script row describe the blocked state
- [x] 8. `OPENSPEC.md` regenerated (`make openspec-index`); `findings.md` written
- [x] 9. Gates green: `make test` (the whole suite; `test_commit_authorship` needs a full clone and `test_amd_backend`'s README check needs `markdown-it-py`, both of which the test image provides), `make openspec-check` as far as this checkout allows, `make architecture-check`, `make lint`
