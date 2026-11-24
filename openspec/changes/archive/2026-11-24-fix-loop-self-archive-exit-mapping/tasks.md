# Tasks: fix-loop-self-archive-exit-mapping

- [x] Add the `[self-archive] verdict=<v>` marker to `scripts/self_archive_guard.py` (all four outcomes, including the unreadable-baseline path)
- [x] Branch `scripts/fix_loop.sh` on the verdict marker, keeping a distinct `verdict=dismantled` note
- [x] Extend `tests/test_self_archive_guard.py`: restored-dismantle marker, clean-tree ok marker, unreadable-baseline marker, real-block fix-loop driver
- [x] Prove the new guards RED against the base revision's `scripts/self_archive_guard.py` / `scripts/fix_loop.sh` (base: PASSED 33 | FAILED 8)
- [x] Run `make lint`, the focused module and `make openspec-check`; regenerate `OPENSPEC.md`
- [x] Archive the change onto the branch (`make openspec-archive NAME=fix-loop-self-archive-exit-mapping`) and regenerate `OPENSPEC.md`
