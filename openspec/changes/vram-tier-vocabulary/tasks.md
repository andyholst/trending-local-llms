# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `check_vram_tier_vocabulary` reports the distribution, unit-less values and out-of-category values, and never fails
- [x] 3. It is registered under the `data` stage (rule 6d)
- [x] 4. The two unit-less store values are normalised (`48`→`48GB`, `8`→`8GB`) and the README re-rendered with `make render-readme`
- [x] 5. `tests/test_vram_tier_vocabulary.py` covers the report, the degenerate stores, the real store and the wiring
- [x] 6. Verified RED on the pre-change tree (the check is missing → the guard fails naming it) and GREEN after (`PASSED 11 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make validate`, `make validate-mapped` and `make openspec-check` green
