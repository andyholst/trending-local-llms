# Tasks: rulebook-store-note-pin-order-1612

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist)
- [x] Replace `note.endswith(CHANGE_2)` with the presence + ascending-order predicate in `tests/test_agents_store_rows.py`
- [x] Prove RED-first: the pre-amendment module reds on this tree (`FAIL … ends with the approved CHANGE 2 clause`)
- [x] Prove GREEN on Order A, and prove Order B passes the same relaxed assertion (scratch `AGENTS.md` copy)
- [x] Prove a MISSING and an OUT-OF-ORDER `#1395` clause each still RED the predicate
- [x] Add `findings/1612.md` and pass `python3 scripts/file_findings.py --check --issue 1612`
- [x] Regenerate `OPENSPEC.md`; run `make lint`, `architecture_check`, `lint_linefeeds`, `check_counter_parity`, `openspec-check`
- [x] Commit, push and amend PR #1600's EXISTING branch with `Closes #1612` alongside `Closes #1586`; record/archive this change on that branch
