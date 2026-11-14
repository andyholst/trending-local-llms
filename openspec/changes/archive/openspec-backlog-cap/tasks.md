# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/openspec_backlog_check.py`: one count, one cap
      (`MAX_ACTIVE_OPENSPEC_CHANGES = 50`), one verdict — exit 0 under the cap with
      `active=<n>/50` printed, exit 1 at it naming every active change + its Issue + the
      `openspec-record-pr` remedy, exit 2 when `openspec/changes/` is missing
- [x] 3. `Makefile`: `openspec-backlog-check` recipe added to `.PHONY` and to
      `openspec-check`'s prerequisite list; `openspec-check`'s help names the cap
- [x] 4. `tests/test_openspec_backlog.py`: planted-fixture tests of the REAL script
      (49 green with headroom, exactly 50 red with remedies, 51 stays red, archive
      excluded, missing tree exit 2) + the REAL Makefile wiring (prerequisite of
      `openspec-check`, which qa-validate runs) — 20/20 green
- [x] 5. `AGENTS.md` §6f: the sentence naming the cap (rule-3c diff, declared on #938)
      + the §8 guard row
- [x] 6. `ARCHITECTURE.md`: §6 target + script rows; `make architecture-refresh`
      regenerated the inventory block (182 lines); `make lint` green
- [x] 7. `make openspec-check` green on the branch; PR opened with the five-section
      body closing #938 (CI state reported honestly on the PR)
