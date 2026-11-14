# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `_stated()` is the one definition of "captured" (model row OR any measurement)
- [x] 3. The `missing` set and the free-text skip both use it
- [x] 4. Guard: a measurement-only value is not missing, not unstructured and not in the signature
- [x] 5. Verified RED on the pre-change `analyse()` (2 failures) and GREEN after (`PASSED 127 | FAILED 0`)
- [x] 6. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 7. `make lint`, `make data-gaps`, `make test` and `make openspec-check` green
