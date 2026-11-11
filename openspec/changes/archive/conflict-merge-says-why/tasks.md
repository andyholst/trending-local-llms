# Tasks

- [x] 1. Write the proposal + `bot-conflict-repair` capability spec for issue #563.
- [x] 2. `scripts/fix_loop.sh`: `merge_base` captures git's own output and branches on whether an unmerged path exists; `<unreadable>` / `<git could not list them>` removed.
- [x] 3. `tests/test_fix_loop.py`: a real repo whose base adds a file the branch has untracked — no placeholder, git's reason quoted, no report, the round still runs, nothing staged.
- [x] 4. Verified RED against `origin/master`'s `fix_loop.sh` (4 failures, `<unreadable>` printed and the tree left staged) and GREEN after (62 passed); the existing real-conflict test is unchanged and green.
- [x] 5. `findings.md` written; `AGENTS.md` §8 guard row attempted (protected file — see findings if refused).
- [x] 6. `OPENSPEC.md` regenerated; `make lint`, `make openspec-check`, `make architecture-check`, `make findings-check` green.
