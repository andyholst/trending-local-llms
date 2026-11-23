# Tasks

- [x] 1. Route the 3 container-safe keeper PR-body targets through `$(PYTHON_RUN)` with a `python-env-image` prerequisite, each recipe staying a pure `python3 scripts/…` command: `openspec-index-repair-pr-body`, `openspec-invalid-change-repair-pr-body`, `architecture-block-repair-pr-body`.
- [x] 2. Keep `refresh-pr-body`, `pipeline-failure-ledger-pr-body` (measured host-only) and `pr-title`/`pr-body`/`architecture-pr-body` (deferred to #1411) host-side, and document all of them in the Makefile seam block; assert the host-only ones in the proving test.
- [x] 3. Make the `python-env-image` prerequisite silent on stdout (`>&2`) so `make keeper-pr`'s captured body is the body alone.
- [x] 4. Extend `tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container` with the seeded Slice-3 set and the extended exception loop; prove it RED on the pre-change base and GREEN on the head.
- [x] 5. Prove the migrated targets on a real Docker host (each runs in the container; body byte-identical to host Python).
- [x] 6. OpenSpec change dir `os-agnostic-make-pr-body-batch-seam` (proposal + GWT spec + ticked tasks); regenerate `OPENSPEC.md`; `make openspec-check` green.
- [x] 7. Full in-container `make test` exit 0; `make pr-message-check`, `make lint` green.
