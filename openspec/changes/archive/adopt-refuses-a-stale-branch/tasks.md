# Tasks

- [x] 1. Write the proposal + `worktree-base` capability spec for issue #592.
- [x] 2. `mode_adopt` computes the commits the branch carries that the base does not have, BEFORE any stash/checkout.
- [x] 3. Above `RESUME_MAX_AHEAD` (default 20) it REFUSES (exit 1) naming the branch, both counts and the remedy; `--resume-stale` / `RESUME_STALE=1` is the explicit override.
- [x] 4. `tests/test_worktree_base.py`: an abandoned branch is refused with the run's work, HEAD and the stash list untouched; the override adopts it; a re-run's own branch is still adopted.
- [x] 5. Verified RED on `origin/master`'s `worktree_base.py` (6 failures) and GREEN after (118 passed).
- [x] 6. `findings.md` written (the branch stays open for the next sweep; the threshold is a guess).
- [x] 7. `make openspec-check`, `make architecture-check`, `make lint` green.
