# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `_comments()` reads the whole thread with `--paginate` + `--jq .[]` (the `issue_thread.py` shape), parsed line-by-line, a failed read still `GhError`
- [x] 3. `tests/test_sweep_outcome.py` gains a >100-comment-thread guard: marker on the last comment, second `--post` for the same run posts nothing, the `gh` call recorded with `--paginate` (verified RED on the old script: 3 FAILs — double-post, missing `--paginate`, `per_page=100`)
- [x] 4. `AGENTS.md` §8 row for `test_sweep_outcome` names the long-thread guard
- [x] 5. `OPENSPEC.md` regenerated; index + tasks checks green
- [ ] 6. `make lint` and the sweep-outcome test green locally; `make openspec-check` / `make test` green in CI
