# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `CPU_ONLY_MARKER` is strict (bare marker forms only — a sentence naming a GPU is not it)
- [x] 3. `vram_need()` returns `("CPU only", "declared")` before any numeric fallback
- [x] 4. `README.md` re-rendered with `make render-readme` (no store churn)
- [x] 5. Guard extended: the three spellings, the prose value, and the rendered cell
- [x] 6. Verified RED on the pre-change function (4 failures) and GREEN after (76 passed, 0 failed)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make validate` and `make openspec-check` green
