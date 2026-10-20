# Tasks

- [x] 1. The measured gap is recorded on #475 (a conflicting PR runs no workflows, so nothing dispatches a repair)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `pr_health.py --repair`: dispatch fix-bot for a silent `ci/…` PR, capped per PR
- [x] 4. A human's branch is reported, never dispatched to
- [x] 5. `fix_loop.sh`: a conflicted base merge is KEPT and its hunks go to the round's report
- [x] 6. Generated artifacts are documented as REGENERATED, never hand-merged
- [x] 7. An unresolved conflict is RED by definition; the merge is COMPLETED when the index is clean
- [x] 8. Unresolved after the last round: `git merge --abort`, so nothing half-merged is pushed
- [x] 9. `make pr-health REPAIR=1` + the workflow step (PAT for dispatch, default token for the comment)
- [x] 10. Tests: 8 conflict-repair checks in `test_fix_loop.py`, 4 repair-target checks in `test_pr_health.py`
- [x] 11. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 12. `findings.md` written; the owed AGENTS.md §6b/§8 wording filed as its own issue (protected file)
