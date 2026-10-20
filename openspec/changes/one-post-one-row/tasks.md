# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `_real_post()` treats only `/status/<id>` as a post identity
- [x] 3. `_collapse_one_post()` keeps the highest t/s, maxes counters, fills dimensions only
- [x] 4. `merge_engines` runs the collapse before its existing grouping
- [x] 5. `COUNTER_FIELDS` named once beside `MEASUREMENT_DIMENSION_FIELDS`
- [x] 6. Guard covers the measured case, posts/engines distinctness, placeholders, fill-only and the ingest seam
- [x] 7. Verified RED on the pre-change script (both symbols missing) and GREEN after (`PASSED 13 | FAILED 0`)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make validate`, `make test` and `make openspec-check` green
