# Tasks

- [x] 1. Route the 5 post-`image-ensure` guard targets through `$(PYTHON_RUN)` with a `python-env-image` prerequisite, each recipe staying a pure `python3 scripts/…` command: `openspec-tasks-check`, `openspec-index-check`, `findings-check`, `check-secret-output`, `query-coverage`.
- [x] 2. Document the host-only exceptions (gh-bound verifiers, `lint`/`lint-fix`, `check-commit-authorship`, already-wrapped `validate`/`update_trending`/`data-gaps`) in a Makefile block right at the `PYTHON_RUN` seam; do NOT route them this slice.
- [x] 3. Extend `tests/test_workflows.py` `test_python_env_seam_...` to assert each of the 5 migrated targets carries `python-env-image` + `$(PYTHON_RUN) … pure command`, and that the host-only exceptions stay host-side (no `$(PYTHON_RUN)`).
- [x] 4. OpenSpec change dir `os-agnostic-make-guard-batch-seam` (proposal + GWT spec + ticked tasks); regenerate `OPENSPEC.md` via `make openspec-index`; `make openspec-check` green.
- [x] 5. Prove the migrated targets run green through the container on a Docker host; full `make test` exit 0; `make lint-fix` last.
