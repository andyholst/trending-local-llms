# Proposal: host-python-env-silence-1457

Issue: #1457
PR: #1461
**Capability:** `host-artifact-silence`

## Why

PR #1451 routed `pr-title`, `pr-body` and `architecture-pr-body` through the
`python-env-image` prerequisite + `$(PYTHON_RUN)` seam. On a HOST runner
(`/.dockerenv` absent, so `IN_CONTAINER` is empty) that prerequisite runs
`python3 scripts/ensure_image.py ensure-python`, and BOTH make's echoed recipe line
and the script's own stdout go to fd 1. All three targets are consumed by exact-stdout
capture on the host: `TITLE=$(make pr-title …)`, `make pr-body … > pr-body.md`, and the
keeper body composed by `make keeper-pr`. The ensure noise therefore lands in the
implementation PR title/body and the architecture keeper body. CI stayed green because
`make test` runs INSIDE the container, where `IN_CONTAINER=1` selects the silent `@:`
escape and the host branch is never exercised.

## What Changes

- Silence the `python-env-image` HOST branch: prefix its recipe with `@` and move
  `ensure_image.py`'s stdout off fd 1 (`>&2`). The in-container `@:` escape and every
  other routed target stay unchanged.
- Extend the workflow redirect guard to walk a redirected target's PREREQUISITE
  recipes (conditional branches included) and refuse a non-silent one, so this class
  cannot come back silently.
- Add a forced-host execution assertion to `tests/test_pr_body.py` (R1/R2), a host
  dry-run silence assertion to `tests/test_python_env_in_container.py` (R3), the guard
  extension to `tests/test_workflows.py` (R4), and a body-purity assertion to the real
  `make keeper-pr` fixture in `tests/test_architecture_bot.py` (R5).

## Impact

Makefile + tests only. No data, contract, README, workflow, target/stage/job or image
change, and no behaviour change for any other routed target. The in-container path is
byte-identical; on the host the ensure diagnostic moves from fd 1 to stderr.

## Not covered

- No change to `scripts/pr_body.py` — neither `render` nor `title`.
- No new gate target, pipeline job or schedule; no AGENTS.md rule change.
