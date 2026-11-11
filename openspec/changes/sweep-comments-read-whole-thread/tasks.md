# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [ ] 2. `_comments()` reads the whole thread with `--paginate` + `--jq .[]` (the `issue_thread.py` shape), parsed line-by-line, a failed read still `GhError`
- [ ] 3. `tests/test_sweep_outcome.py` gains a >100-comment-thread guard: marker on the last comment, second `--post` for the same run posts nothing, the `gh` call recorded with `--paginate`
- [ ] 4. `AGENTS.md` §8 row for `test_sweep_outcome` names the long-thread guard
- [ ] 5. `OPENSPEC.md` regenerated; index + tasks checks green
- [ ] 6. `make lint` and the sweep-outcome test green locally; `make openspec-check` / `make test` green in CI
