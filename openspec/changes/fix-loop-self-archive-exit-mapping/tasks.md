# Tasks: fix-loop-self-archive-exit-mapping

- [x] Add the `[self-archive] verdict=<v>` marker to `scripts/self_archive_guard.py` (all four outcomes, including the unreadable-baseline path)
- [x] Branch `scripts/fix_loop.sh` on the verdict marker, keeping a distinct note for `unrecovered`
- [x] Extend `tests/test_self_archive_guard.py`: restored-dismantle marker, unreadable-baseline marker, fix-loop branch pin
- [x] Prove the new guards RED against the base revision's `scripts/self_archive_guard.py` / `scripts/fix_loop.sh`
- [ ] Run `make lint`, the focused module and `make openspec-check`; regenerate `OPENSPEC.md` and the `ARCHITECTURE.md` inventory block
- [ ] Archive the change onto the branch, open the PR with `closes #1582`, hand over to `tll-reviewer`
