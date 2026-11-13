# Tasks

- [x] 1. The tracked change exists (this directory) before the code edits
- [x] 2. `scripts/self_archive_guard.py`: `snapshot` records the active+archived OpenSpec changes as JSON; `check` reports a baseline-active change gone from the tree (exit 1), with `SELF_ARCHIVE_RESTORE=1` restoring first (archive copy moved back + index re-staged, else from `SELF_ARCHIVE_REF`, else `unrecoverable`); no baseline exits 2
- [x] 3. `scripts/fix_loop.sh`: baseline snapshot after `merge_base` (git checkout only, `SELF_ARCHIVE_REF=HEAD` exported), guard after EVERY round before the green re-check, dismantle report folded into `$NOTES`, both targets added to `arch-calls:`
- [x] 4. `Makefile`: `self-archive-snapshot` / `self-archive-guard` (host-only git gates, the `check-commit-authorship` pattern)
- [x] 5. `tests/test_self_archive_guard.py` (8 tests, 15 checks) green against the real script
- [x] 6. `tests/test_fix_loop.py::test_a_round_that_archives_its_own_change_is_refused_and_restored` green end to end AND verified RED against the pre-change `scripts/fix_loop.sh` (5 checks fail on the old code)
- [x] 7. `AGENTS.md` §8 guard row (rule 6c) + `ARCHITECTURE.md` target rows and §6 script row (rule 6h) + §10 inventory regenerated + `OPENSPEC.md` regenerated
- [ ] 8. `make lint`, `make architecture-check`, `make openspec-index-check`, `make openspec-check` and the full container `make test` green on this branch
- [ ] 9. PR opened (`closes #812`, five-section body) with the AGENTS.md diff called out for rule 3c sign-off; monitored until `validate` + `live-smoke` are green and `auto-merge` lands it; the change archived at the PR via `make openspec-record-pr` per rule 6f
