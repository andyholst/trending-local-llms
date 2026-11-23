# Tasks: python-env-seam-in-container

- [x] Give the ONE `PYTHON_RUN` assignment its `$(if $(IN_CONTAINER),…)` fork
- [x] Skip `python-env-image`'s ensure in-container with a silent `@:` escape
- [x] Route `pr-title`, `pr-body`, `architecture-pr-body` through `python-env-image` + `$(PYTHON_RUN)`
- [x] Extend the Slice-1/2 seam guard with the three targets; assert `refresh-pr-body` stays host-only
- [x] Add `tests/test_python_env_in_container.py` (expansion fork, silent escape, prose rows)
- [x] Force-execute the in-container branch in `tests/test_pr_body.py`
- [x] Restate the three stale `ARCHITECTURE.md` rows
- [x] Regenerate `OPENSPEC.md`; run the focused checks, `make lint` and `make architecture-check`
- [x] Push the branch; `qa-validate` proves the full canonical in-container `make test`
