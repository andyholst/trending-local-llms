# Tasks

- [x] 1. Proposal + `owed-row-ledger` capability spec.
- [ ] 2. `scripts/bot_markers.py`: register the owed-row ledger marker (name, shape, parser) as a
      ledger key distinct from bot windows and dedup keys.
- [ ] 3. `scripts/owed_rows_check.py`: read open queue issues through `scripts/issue_queue.py`,
      parse owed-row markers from each thread, search AGENTS.md, print landed/outstanding with
      evidence lines; loud (exit 2) on a malformed marker or unreadable ledger.
- [ ] 4. `Makefile`: `_owed-rows-check` internal recipe + public `owed-rows-check` target
      (host-side gh verifier, documented like `queued-alarm`).
- [ ] 5. `.github/workflows/queued-alarm.yml`: alarm job step calling the target.
- [ ] 6. `tests/test_owed_rows.py`: real script against stub-`gh` PATH shim + recorded fixtures
      (landed / outstanding / malformed / no-marker); pipeline-call guard.
- [ ] 7. Post the owed-row marker comments for the #523 backlog rows on the issues (comments, not
      body edits — rule 6j), generated through `scripts/bot_markers.py`.
- [ ] 8. `AGENTS.md`: §8 row for the new guard; ARCHITECTURE.md row + `make architecture-refresh`.
- [ ] 9. Verified: sabotage run (landed-row test fails without the check), `make test`,
      `make lint`, `make openspec-check`, `make architecture-check`, live
      `make owed-rows-check REPO=...` recorded on the PR.
