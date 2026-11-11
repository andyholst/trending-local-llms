# Tasks

- [x] 1. The tracked change exists (this directory) before the code edit
- [x] 2. `parse()` strips leading markdown decoration and matches the key case-insensitively, tolerating a wrapped or spaced colon
- [x] 3. The verdict is the FIRST word of the value with emphasis/quote/period decoration stripped; a trailing reason no longer makes it unknown
- [x] 4. `REFINED`/`EVIDENCE`/`REASON` tolerate the same decoration and keep their content
- [x] 5. Every existing refusal is preserved: unknown verdict, no TRIAGE line, close without EVIDENCE, refine without a restatement
- [x] 6. `tests/test_issue_triage.py` proves each measured decorated shape is read and three near-misses are refused with no write
- [x] 7. Verified RED on the pre-change parser (all eleven decorated shapes refused) and GREEN after (`PASSED 99 | FAILED 0`)
- [x] 8. `ARCHITECTURE.md`'s inventory row describes the tolerance and the refusals it keeps
- [x] 9. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 10. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
