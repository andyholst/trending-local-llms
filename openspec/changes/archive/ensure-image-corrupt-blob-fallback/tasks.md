# Tasks

- [x] 1. The tracked change exists (this directory) before any code or test edit
- [x] 2. `tests/test_ensure_image.py`: docker stub answers `pull` with
      `FAKE_DOCKER_PULL_ERROR`; new test locks the corrupt-blob fallback (base +
      test), the loud non-blob pull failure, and the unchanged healthy states —
      RED on the pre-change seam (5 checks), green after it (118/118)
- [x] 3. `scripts/ensure_image.py`: `_pull` captures docker's output,
      `_pull_or_fail` classifies it (`BlobsUnfetchable` vs loud raise), and
      `ensure_base` / `ensure_test` / `ensure_openspec` fall back to building this
      revision's Dockerfile with truthful verdict lines
- [x] 4. Gates green on the exact head: `tests/test_ensure_image.py`,
      `tests/test_makefile_only.py`, `make lint`, `make test`
- [x] 5. `ARCHITECTURE.md` §6 row for `scripts/ensure_image.py` names the
      third state (issue #1118) and `make architecture-refresh` regenerated the
      inventory block; `make architecture-check` green
- [x] 6. AGENTS.md §8 row for the new guard test (rule 6c) — attended change,
      row landed in the same branch (rule 3c sign-off is this reviewed PR)
