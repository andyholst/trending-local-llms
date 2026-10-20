# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `card_gap_reason()` is the one definition of "why this model has no card row"
- [x] 3. `check_card_gap_report` prints the count, the split and the actionable model names; never fails
- [x] 4. Registered under the `readme` stage (rule 6d)
- [x] 5. Guard covers the reasons, the report, degenerate stores, the real store and the wiring
- [x] 6. Verified RED on the pre-change tree (both symbols missing) and GREEN after (`PASSED 17 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make validate` and `make openspec-check` green
