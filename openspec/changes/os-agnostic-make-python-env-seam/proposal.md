# OS-agnostic make — python-env image + PYTHON_RUN seam (Slice 1)

**Issue:** [#712](https://github.com/andyholst/trending-local-llms/issues/712)
**Capability:** `os-agnostic-make-python-env-seam`

## Why

Today `make` is not OS-agnostic: the OpenSpec CLI runs in its own image, but
~100 private `_command` recipes still invoke `python3 scripts/…` directly on the
HOST. A host without that Python/those deps cannot run those targets. Slice 1
lands the smallest reviewable unit of the owner's directive — the python-env
image + one seam through which a `_command` recipe runs in a Linux container —
and proves it by migrating 2 targets (`openspec-index`, `architecture-check`).

## Delivery (non-breaking)

Only the seam is added; the two migrated recipes run inside the container
instead of on host Python. No existing target's behavior changes; no
schema/contract/API/table/data-shape change.

- `Dockerfile.python-env` — a plain `python:3.12-slim` + the pinned runtime deps
  (`requirements.txt`) + git. NOT the agent image (no Hermes/nerve).
- `scripts/ensure_image.py` — `PYTHON_FILES`/`python_hash()`/`python_tag()`/
  `ensure_python()`; wired into `tags` (new `PYTHON_TAG`), `ensure`
  (`image-ensure` also ensures python-env), `decide` (new `publish_python_env` /
  `python_env_tag` / `python_env_published`).
- `Makefile` — `PYTHON_RUN` seam macro (docker-run into the python-env image
  with `-v "$$PWD":/workspace -w /workspace -e PYTHONUNBUFFERED=1`, as the
  invoking user) + `python-env-image` ensure target. `openspec-index` and
  `architecture-check` migrated: recipe stays a pure `python3 scripts/…` call,
  prefixed by `$(PYTHON_RUN)`; both carry `python-env-image` as a prerequisite.
- `ARCHITECTURE.md` — §3 table gained the `python-env-image` row; the generated
  inventory refreshed.
- `OPENSPEC.md` — regenerated index: 183 active / 10 archived (this also fixes
  the stale count-line left on master by the #722/#725 concurrent merge,
  issue #526).

## Proof

- `make openspec-index` and `make architecture-check` run through the
  container, proven on the host (Docker present).
- `tests/test_ensure_image.py` — python-env tag/hash tests; `tests/test_workflows.py`
  — asserts the migrated recipes route through the `PYTHON_RUN` seam.
