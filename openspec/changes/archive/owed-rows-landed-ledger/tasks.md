# Tasks

- [x] 1. Proposal + `owed-row-ledger` capability spec.
- [x] 2. `scripts/bot_markers.py`: register the owed-row ledger marker (name, shape, parser) as a
      ledger key distinct from bot windows and dedup keys.
- [x] 3. `scripts/owed_rows_check.py`: list open issues through the same `gh` seam as the other
      live alarms, reuse `issue_queue.QUEUE_LABELS` and `bot_markers.parse_owed_rows` (one
      definition each — no second copies), read each WHOLE thread paginated, search the needle
      inside the declared `## <id>.` section of AGENTS.md, print landed/outstanding with evidence
      lines; loud (exit 2) on a malformed marker, an unknown section or an unreadable ledger.
- [x] 4. `Makefile`: `_owed-rows-check` internal recipe + public `owed-rows-check` target
      (host-side gh verifier, documented like `queued-alarm`).
- [x] 5. `.github/workflows/queued-alarm.yml`: alarm job step calling the target.
- [x] 6. `tests/test_owed_rows.py`: real script against stub-`gh` PATH shim + recorded fixtures
      (landed / outstanding / wrong-section / comment-marker / malformed / unknown-section /
      no-marker / unreadable); pipeline-call guard; no-second-copy guard on the marker shape.
- [x] 7. Ledger stamp on the open ledger issue: #521-class backlog issues (#212 #314 #322 #324
      #369 #380 #385 #405) are ALL CLOSED already, so no stamp is owed on them; the one open
      ledger issue #523 carries the marker comment, generated through `scripts/bot_markers.py`.
- [x] 8. `AGENTS.md`: §8 row for the new guard; ARCHITECTURE.md target row (§2), script row (§6),
      queued-alarm job prose (§4) and `make architecture-refresh` (§10 regenerated).
- [x] 9. Verified: sabotage run (removing the section-scope makes
      `test_a_needle_landed_in_the_wrong_section_is_not_landed` FAIL, restored suite green),
      `make lint` green, `make architecture-check` green, live
      `make owed-rows-check REPO=andyholst/trending-local-llms` run green (exit 0, 36 open
      queue issues reported `NO MARKER`) — recorded on the PR.
