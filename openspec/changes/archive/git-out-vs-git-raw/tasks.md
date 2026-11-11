# Tasks

- [x] 1. Write the proposal + `worktree-base` capability spec for issue #504.
- [x] 2. `scripts/worktree_base.py`: `git_raw` (stdout exactly as git wrote it) beside `git_out`, whose docstring now states the stripping and names `git_raw` for a record.
- [x] 3. `tests/test_worktree_base.py::test_git_out_strips_and_git_raw_does_not`: the leading status byte, the `-z` NUL separators, a whole path through `git_raw`, and the mangled path through `git_out`.
- [x] 4. Verified GREEN (114 passed); the mangled-path check is the measured defect, so it fails on a `git_out`-based parser by construction.
- [x] 5. `findings.md` written.
- [x] 6. `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
