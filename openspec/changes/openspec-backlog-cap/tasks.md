# Tasks

- [ ] 1. The tracked change exists (this directory) before any code edit
- [ ] 2. `scripts/openspec_backlog_check.py`: one count, one cap
      (`MAX_ACTIVE_OPENSPEC_CHANGES = 50`), one verdict — exit 0 under the cap with
      `active=<n>/50` printed, exit 1 at it naming every active change + its Issue + the
      `openspec-record-pr` remedy, exit 2 when `openspec/changes/` is missing
- [ ] 3. `Makefile`: `openspec-backlog-check` recipe added to `.PHONY` and to
      `openspec-check`'s prerequisite list; `openspec-check`'s OK line names the cap
- [ ] 4. `tests/test_openspec_backlog.py`: planted-fixture tests of the REAL script
      (49 green with headroom, exactly 50 red with remedies, archive excluded, missing
      tree exit 2) + the REAL Makefile wiring (prerequisite of `openspec-check`, which
      qa-validate runs)
- [ ] 5. `AGENTS.md` §6f: one sentence naming the cap (rule-3c diff, declared on #938)
- [ ] 6. `ARCHITECTURE.md`: §6 row for the new script; `make architecture-refresh`
      regenerates the inventory block
- [ ] 7. `make openspec-check`, `make test` and `make lint` green on the branch; PR
      opened with the five-section body closing #938
