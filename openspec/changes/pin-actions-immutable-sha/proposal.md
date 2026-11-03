# Immutable-SHA pin guard for workflow `uses:` refs and tool-image tags

**Issue:** [#735](https://github.com/andyholst/trending-local-llms/issues/735)
**Capability:** `pin-actions-immutable-sha`

## Why

Every third-party GitHub Action in `.github/workflows/**` is referenced by a
mutable tag (`actions/checkout@v4`, `docker/setup-buildx-action@v3`, …). A tag
can be moved by its owner, so a workflow that "pinned" a version by tag can
silently start running different code on the next run — a supply-chain risk with
no guard. The same holds for third-party container images the fleet runs as
tools (`ghcr.io/gitleaks/gitleaks:v8.30.1`): a mutable tag can be re-pointed.

This change adds the guard that REFUSES a mutable third-party ref, so a new
mutable ref cannot merge. It does not migrate the existing refs (that is the
later #714/#715 migration slices); the current mutable refs are on an explicit
allowlist, each with an "allow-till <issue>" deadline, so master stays green
while a NEW mutable ref is refused.

## What Changes

- **`scripts/action_pin_check.py`** — a fail-closed guard over two surfaces:
  - **Workflow `uses:`** — every third-party `uses: <owner>/<repo>@<ref>` in
    `.github/workflows/**` must be a 40-hex commit SHA or on the explicit
    `ALLOWED_WORKFLOW_REFS` allow-ref list. Own reusable workflows
    (`./.github/workflows/…`) and `docker://` refs are exempt.
  - **Tool-image seam** — a third-party image tag named in the Makefile
    `*_IMAGE :=` refs, `scripts/*.py` or a Dockerfile `ARG` must be pinned: a
    digest (`@sha256:…`) or the fleet-owned `<sha12>` tag form. A bare mutable
    `:vX.Y.Z` / `:latest` is refused. Fleet-owned images (`trending-local-llms*`
    and `ghcr.io/andyholst/trending-local-llms*`) are exempt.
- **`make action-pin-check`** — a Makefile target routing the guard through the
  `PYTHON_RUN` python-env seam (issue #712 convention), plus the script's unit
  test wired into `make test`.
- **Wire into the CI gate** — `qa-validate`'s `validate` job runs
  `make action-pin-check` after `image-ensure`, so a mutable third-party ref
  refuses the PR and cannot merge.
- **Allowlist with deadlines** — the current mutable refs (7 workflow `uses:`
  tags + gitleaks `v8.30.1`) are on `ALLOWED_WORKFLOW_REFS` /
  `ALLOWED_IMAGE_REFS`, each documented "allow-till #714/#715" (the migration
  slices that will pin them). A NEW mutable ref not on the list is refused.

## #737 (#714 Slice 2): the 37 refs are migrated to immutable SHAs

This change dir stays the single tracked change for #714; Slice 2 extended it.
All 37 third-party workflow `uses:` refs in `.github/workflows/**` are pinned to
the current immutable 40-hex commit SHA of the action revision for the SAME
major version as the tag they replace:

- `actions/checkout@v4` ×20 → `11d5960a…`
- `docker/setup-buildx-action@v3` ×4 → `8d2750c6…`
- `actions/upload-artifact@v4` ×4 → `ea165f8d…`
- `docker/login-action@v3` ×3 → `c94ce9fb…`
- `docker/build-push-action@v6` ×3 → `10e90e36…`
- `actions/cache@v4` ×2 → `0057852b…`
- `actions/download-artifact@v4` ×1 → `d3f86a10…`

Each SHA was verified to exist in its upstream repo and to back the same-major
tag it replaces. After the migration `ALLOWED_WORKFLOW_REFS` is empty — the #714
allow-till deadline is satisfied with no dangling hold — so a NEW mutable
third-party workflow ref is refused (fails closed). `make action-pin-check` is
GREEN on master-as-is. The gitleaks tool-image ref stays on
`ALLOWED_IMAGE_REFS` (allow-till #715).

## Out of scope (later slices / other issues)

- Migrating the workflow `uses:` refs from tag → SHA — DONE in #737 (Slice 2).
- Pinning gitleaks / the tool images through `ensure_image.py`'s `<sha12>`
  scheme (a later #715 slice).
- README/comment "how to bump an action" friction docs (#714 Slice 3).
