# Tasks: agents-store-rows

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist)
- [x] Land the three `AGENTS.md` §7b/§8 texts VERBATIM from the reviewer-approved landing text (`issuecomment-7128719625`) — rule 3c sign-off: reviewer ACCEPT on the issue + the owner-authorised 2026-11-24 protected-file landing
- [x] Add `tests/test_agents_store_rows.py`, reading the real `AGENTS.md` and locking all three texts (RED on the base, GREEN on the approved text)
- [x] Regenerate `OPENSPEC.md`; run `make lint`, `make architecture-check`, `make openspec-check`
- [x] Commit, push and open the READY PR carrying `Closes #1482` in BOTH title and body; record/archive this change on that branch
