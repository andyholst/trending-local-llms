# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `--render-only` renders from the store as of its `generated_utc` and returns before ingest/write/snapshot
- [x] 3. The `> Last generated:` line is preserved, so a re-run is a no-op
- [x] 4. `make render-readme` + `_render-readme` follow the repo's docker-wrapper pairing
- [x] 5. `check_readme_generated` names `make render-readme` for a docs change (and `make merge` for new data)
- [x] 6. `ARCHITECTURE.md` describes the target (rule 6h); `architecture-check` green
- [x] 7. `tests/test_render_only.py` drives the real script through its env seams (store unchanged, no snapshot, no-op re-run, stale repair, timestamp kept, wiring)
- [x] 8. Verified RED on the pre-change script (6 failures) and GREEN after (`PASSED 11 | FAILED 0`)
- [x] 9. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 10. `make lint`, `make test`, `make validate`, `make architecture-check` and `make openspec-check` green
