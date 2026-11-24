# Tasks: rulebook-findings-seam-row-1602

- [x] Create the tracked change before any edit (proposal + capability spec + task checklist)
- [x] Land the `AGENTS.md` §8 row for `tests/test_findings_seam.py` VERBATIM from the reviewer-approved landing text (`issuecomment-7133012801`), anchored on the row TEXT after `tests/test_push_and_verify_guard.py`
- [x] Add `tests/test_findings_seam.py::test_rulebook_section_8_carries_the_analysis_seam_row` plus its one `main()` call — no new file, no Makefile/target change
- [x] §8-only scope held: no §7b bullet and no clause appended to the shared `Rule 3c note`
- [x] RED on the base (pin without the row: exit 1) and GREEN on the landing head (`PASSED 26 | FAILED 0`) executed
- [x] `python3 scripts/owed_rows_check.py --repo andyholst/trending-local-llms` reports `#1602 … LANDED AGENTS.md:<line>` on the landing tree
- [x] Regenerate `OPENSPEC.md`; `make lint`, `make architecture-check`, `make openspec-check` green
- [x] Commit, push and open the READY PR carrying `Closes #1602` in BOTH title and body; record/archive this change on that branch
