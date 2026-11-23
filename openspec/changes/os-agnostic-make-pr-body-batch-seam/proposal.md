# OS-agnostic make — the keeper PR-body batch behind the PYTHON_RUN seam (Slice 3)

**Issue:** [#1399](https://github.com/andyholst/trending-local-llms/issues/1399)
**Capability:** `os-agnostic-make-pr-body-batch-seam`

## Why

Slice 1 (PR #727) landed the `python-env` image + the ONE `PYTHON_RUN` seam;
Slice 2 (PR #730) routed the guard/validator batch. This is **Slice 3**: route the
keeper PR-body composers behind the same seam, so a runner with Docker but not
the pinned Python/deps composes the keeper PR bodies. The batch is one script
family (`pr_body.py` and the `*-print-pr-body` composers), all stdlib-only.

`#712` is the reopened umbrella; `#1399` is this slice's holder so `pr_closure`
has a closing target (this merge does NOT close #712).

**Scope is the reduced slice the planner ruled on #1399 (issuecomment-7102333970).**
The design listed 8 targets; measured, only these 3 are container-safe AND
exercisable by the in-container suite. The rest are split out (below).

## Delivery (non-breaking)

Only recipes change: each migrated target gains a `python-env-image`
prerequisite and a `$(PYTHON_RUN)` prefix while its command stays a pure
`python3 scripts/…` call (no per-recipe docker harness). No schema/contract/API/
table/data-shape change; no existing behaviour changes except that the migrated
composers run inside the python-env container instead of on host Python
(identical stdlib inputs, byte-identical output).

**Migrated through `PYTHON_RUN` (3 targets):**

- `openspec-index-repair-pr-body` — `openspec_index_repair.py --print-pr-body …`
- `openspec-invalid-change-repair-pr-body` — `openspec_invalid_change_repair.py --print-pr-body …`
- `architecture-block-repair-pr-body` — `architecture_block_repair.py --print-pr-body …`

**Host-only exceptions (documented in the Makefile seam block and asserted by the
proving test) that are deliberately NOT routed:**

- the `pr-closure.yml` trio (`pr-message-check`, `issue-message-check`,
  `commit-message-check`): that workflow runs them on a webhook BEFORE any
  image-ensure, so routing them would force a python-env build at the top of the
  closure gate on every event.
- `refresh-pr-body` — its default path (the only way `refresh-bot.yml:700` calls
  it) composes the refresh WINDOW through `gh api` (`scripts/refresh_run_block.py`;
  no `gh` in the image, and `PYTHON_RUN` forwards no run env), and its
  `WINDOW_FILE` is a host path the container cannot see. Measured: exit 2
  (REFUSED) / exit 1 (FileNotFoundError); `tests/test_pr_body.py` reds.
- `pipeline-failure-ledger-pr-body` — its `RUN_URL` is read from the ENV
  (`os.environ.get("RUN_URL")`), which `PYTHON_RUN` does not forward, and its
  `LEDGER` is a host path. Measured: host `sweep (<url>)` vs container `sweep ()`.
- `pr-title` / `pr-body` / `architecture-pr-body` — pure and container-clean on a
  Docker host, but `make test` runs the suite INSIDE the docker-less test image,
  so a docker-routed recipe cannot be driven from it (21 in-container reds,
  measured). Deferred to **#1411**.

## One hygiene change (flagged on #1399)

`python-env-image`'s recipe is now `@python3 scripts/ensure_image.py ensure-python
>&2`, so the prerequisite writes its status to stderr instead of stdout. Without
it the keeper body's captured stdout (`make keeper-pr` captures the body target)
would lead with the ensure status line. `ensure_image.py`, `PYTHON_RUN`, the image
and every workflow are untouched.

## Proof

- `tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container`
  seeds the 3 migrated targets (each must carry `python-env-image` +
  `$(PYTHON_RUN) … pure command`) and the host-only exceptions (each must carry
  no `$(PYTHON_RUN)`); RED on the pre-change base, GREEN on the head.
- A real container run on this Docker host: each migrated target expands to
  `docker run … python-env python3 scripts/…` and the composed body is
  byte-identical to the host-python output.
- Full in-container `make test` exit 0; `make openspec-check` green; `make lint`
  green.
