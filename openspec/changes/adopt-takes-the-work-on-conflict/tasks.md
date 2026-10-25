# Tasks

- [x] 1. Write the proposal + `worktree-base` capability spec for issue #583.
- [x] 2. `scripts/worktree_base.py`: a conflicted re-apply takes THIS RUN's side per path, stages it, leaves no marker, and reports `merge_conflict=<paths>`.
- [x] 3. `tests/test_worktree_base.py`: the resolved content, an EMPTY `git grep '^<<<<<<<'`, and the named resolution.
- [x] 4. Verified RED against `origin/master`'s `worktree_base.py` (3 failures, marker left in `f.txt`) and GREEN after (109 passed).
- [x] 5. `findings.md` written; `AGENTS.md` §8 row attempted (protected file — recorded if refused).
- [x] 6. `OPENSPEC.md` regenerated; `make lint`, `make openspec-check`, `make architecture-check` green.
