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

## Out of scope (later slices / other issues)

- Migrating the workflow `uses:` refs from tag → SHA (a later #714 slice).
- Pinning gitleaks / the tool images through `ensure_image.py`'s `<sha12>`
  scheme (a later #715 slice).
- README/comment "how to bump an action" friction docs (#714 Slice 3).
