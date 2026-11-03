# Tasks

- [x] 1. Draft `Dockerfile.python-env` (plain `python:3.12-slim` + pinned runtime deps + git; no Hermes/nerve — separate from the agent base, issue #712 Slice 1).
- [x] 2. `scripts/ensure_image.py` — `PYTHON_FILES`, `python_hash()`, `python_tag()`, `ensure_python()` (local-build: builds from `Dockerfile.python-env` when absent, reuses when present, never probes the registry); wire into `tags` (`PYTHON_TAG`) and `ensure` (image-ensure also ensures python-env); `decide` left unchanged (no publisher in Slice 1); usage text.
- [x] 3. `Makefile` — `PYTHON_IMAGE` + `PYTHON_RUN` seam (`--rm --user … -v "$$PWD":/workspace -w /workspace -e PYTHONUNBUFFERED=1`, pure-command recipes) + `python-env-image` target + final `tuple` dispatch name `python-env-image` in `.PHONY`.
- [x] 4. Migrate `openspec-index` + `architecture-check` through `$(PYTHON_RUN)` with a `python-env-image` prerequisite; recipes stay pure `python3 scripts/…` calls (no per-recipe docker boilerplate).
- [x] 5. `ARCHITECTURE.md` — add `python-env-image` §3 table row; `make architecture-refresh` regenerates the inventory (172 make targets); update the generated count-line framing.
- [x] 6. Build the python-env image locally; `make openspec-index` + `make architecture-check` both run through the container and PASS (proven on host with Docker).
- [x] 7. `OPENSPEC.md` — `make openspec-index` regenerates the index (183 active / 10 archived; also fixes the stale base count-line, issue #526); `make openspec-index-check` green.
- [x] 8. Tests — `tests/test_ensure_image.py` (python-env hash/tag/ensure) + `tests/test_workflows.py` (recipes route through `PYTHON_RUN`, `python-env-image` prerequisite + ensure wiring); full `make test` exit 0; `make openspec-check` green; `make lint-fix` last.
