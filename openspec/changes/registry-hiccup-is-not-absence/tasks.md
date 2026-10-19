# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `published()` reads docker's own absence wording; any other failure raises `RegistryUnknown`
- [x] 3. `main()` dispatches through a handler that exits 1 with docker's words, so `ensure-*` and `decide` both fail loudly
- [x] 4. The docker stub can fail like a registry (`FAKE_DOCKER_MANIFEST_ERROR`) and prints the real `manifest unknown:` wording when absent
- [x] 5. The guard covers: hiccup on `ensure-base` (no build), absent tag (builds), hiccup on `decide` (no decision)
- [x] 6. Verified RED on the pre-change script (5 failures — it rebuilt) and GREEN after (`PASSED 83 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
