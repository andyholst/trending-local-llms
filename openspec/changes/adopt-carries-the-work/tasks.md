# Tasks

- [x] 1. Write the proposal + `worktree-base` capability spec for issue #580.
- [x] 2. `scripts/worktree_base.py`: `mode_adopt` stashes a dirty tree before attaching an existing branch and re-applies it after; `merge_conflict=true` on a conflicting re-apply.
- [x] 3. `tests/test_worktree_base.py`: a real repo with a dirty file the branch changed + a new file + an untracked file; the earlier commit intact; the work kept.
- [x] 4. Verified RED against `origin/master`'s `worktree_base.py` (4 failures, reproducing `REFUSED: git checkout -B … would be overwritten`) and GREEN after (107 passed); the first-run (#500) test unchanged.
- [x] 5. `findings.md` written; `AGENTS.md` §8 row attempted (protected file — recorded if refused).
- [x] 6. `OPENSPEC.md` regenerated; `make lint`, `make openspec-check`, `make architecture-check` green.
