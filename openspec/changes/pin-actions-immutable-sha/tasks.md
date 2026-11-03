# pin-actions-immutable-sha

- [x] Add `scripts/action_pin_check.py` — the fail-closed guard over the workflow `uses:` surface (third-party ref must be a 40-hex SHA or on the allow-ref list; own reusable workflows exempt)
- [x] Extend the guard to the tool-image seam — Makefile `*_IMAGE :=`, `scripts/*.py`, Dockerfile `ARG` refs must be pinned (digest or fleet `<sha12>` tag) or allowlisted; fleet-owned images exempt
- [x] Add the `make action-pin-check` target routing through the `PYTHON_RUN` python-env seam
- [x] Wire `make action-pin-check` into `qa-validate`'s `validate` job after `image-ensure`
- [x] Add the current mutable refs to the allowlists (`ALLOWED_WORKFLOW_REFS` / `ALLOWED_IMAGE_REFS`) with allow-till deadlines
- [x] Prove RED where mutable and GREEN where pinned/allowlisted in `tests/test_action_pin.py` (real guard on fixture trees; no docker CLI mocked)
- [x] Assert the guard is wired into the gate in `tests/test_workflows.py` and passes on this repo
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`) and keep `make openspec-check` / `make openspec-archive-check` green
