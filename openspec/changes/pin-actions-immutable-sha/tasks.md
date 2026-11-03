# pin-actions-immutable-sha

- [x] Add `scripts/action_pin_check.py` — the fail-closed guard over the workflow `uses:` surface (third-party ref must be a 40-hex SHA or on the allow-ref list; own reusable workflows exempt)
- [x] Extend the guard to the tool-image seam — Makefile `*_IMAGE :=`, `scripts/*.py`, Dockerfile `ARG` refs must be pinned (digest or fleet `<sha12>` tag) or allowlisted; fleet-owned images exempt
- [x] Add the `make action-pin-check` target routing through the `PYTHON_RUN` python-env seam
- [x] Wire `make action-pin-check` into `qa-validate`'s `validate` job after `image-ensure`
- [x] Add the current mutable refs to the allowlists (`ALLOWED_WORKFLOW_REFS` / `ALLOWED_IMAGE_REFS`) with allow-till deadlines
- [x] Prove RED where mutable and GREEN where pinned/allowlisted in `tests/test_action_pin.py` (real guard on fixture trees; no docker CLI mocked)
- [x] Assert the guard is wired into the gate in `tests/test_workflows.py` and passes on this repo
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`) and keep `make openspec-check` / `make openspec-archive-check` green

## #737 (#714 Slice 2) — migrate the 37 workflow `uses:` refs to immutable SHAs

- [x] Pin all 37 third-party `uses:` refs in `.github/workflows/**` to the current immutable 40-hex commit SHA of the pinned action revision for the SAME major version (checkout@v4 ×20, setup-buildx@v3 ×4, upload-artifact@v4 ×4, login-action@v3 ×3, build-push-action@v6 ×3, cache@v4 ×2, download-artifact@v4 ×1)
- [x] Verify each SHA exists in its upstream repo and backs the same-major tag it replaces
- [x] Empty `ALLOWED_WORKFLOW_REFS` — remove all 37 allow-till-#714 entries; no dangling hold (the #714 deadline is satisfied)
- [x] Keep the gitleaks image ref on `ALLOWED_IMAGE_REFS` (allow-till #715)
- [x] `make action-pin-check` GREEN on master-as-is after the migration (final tag-ref count 0)
- [x] Add a test asserting the pinned workflows contain no tag-based third-party refs, and that the workflow allowlist is empty (`tests/test_action_pin.py`)
- [x] Keep `pin-actions-immutable-sha` the single tracked change dir for #714 (extended, not duplicated); openspec-check green, index current
