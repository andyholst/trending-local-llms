# OS-agnostic make — guard/validator batch behind the PYTHON_RUN seam (Slice 2)

**Issue:** [#729](https://github.com/andyholst/trending-local-llms/issues/729)
**Capability:** `os-agnostic-make-guard-batch-seam`

## Why

Slice 1 (PR #727, merged to `f3e3805`) landed the `python-env` image + the ONE
`PYTHON_RUN` seam and proved it by migrating 2 targets (`openspec-index`,
`architecture-check`). This is **Slice 2**: route the genuinely python-env
container-able **guard/validator batch** behind the same seam, so the CI gates
run those checks in the container instead of on host Python. A host with Docker
but not the pinned Python/deps can then run the whole guard set, not just the
two proof targets.

`#712` is the reopened 4-slice umbrella; `#729` is this slice's per-slice holder
so `pr_closure` has a closing target (this merge does NOT close #712).

## Delivery (non-breaking)

Only recipes change: each migrated target gains a `python-env-image`
prerequisite and `$(PYTHON_RUN)` prefix while its `_command` stays a pure
`python3 scripts/…` call. No schema/contract/API/table/data-shape change; no
existing behavior changes except that the migrated guards run inside the
python-env container instead of on host Python (identical stdlib/git inputs).

**Migrated through `PYTHON_RUN` (the 5 post-`image-ensure` guard targets):**

- `openspec-tasks-check` — `check_openspec_tasks.py $(NAME)` (stdlib)
- `openspec-index-check` — `openspec_index.py --check` (stdlib)
- `findings-check` — `file_findings.py --check` (stdlib parse-only; the `gh`-bound
  `file-findings --file` target stays host-side)
- `check-secret-output` — `check_secret_output.py check` (stdlib)
- `query-coverage` — `query_coverage.py [--top N]` (stdlib + git)

Each recipe is the pure command prefixed by `$(PYTHON_RUN)`; each target lists
`python-env-image` as a prerequisite so the image is ensured before the run
(exactly the Slice-1 pattern). `openspec-tasks-check` + `openspec-index-check`
are prerequisites of `openspec-check`, so the whole OpenSpec gate routes its
host-python checks through the container.

**Host-only exceptions (documented in a Makefile block right at the seam, and
in this proposal) that are deliberately NOT routed:**

- gh-bound verifiers (`openspec-archive-check`, `data-gap-issue`/`data-gap-baseline`,
  `code-review-file`, `file-findings`, `verify-closure`, `pr-closure`,
  `pr-health`) — they read GitHub state / file issues and need the runner's
  `gh` + token; the python-env image deliberately carries no `gh`.
- `lint` / `lint-fix` and `check-commit-authorship` — they run **before**
  `image-ensure` in qa-validate by design ("cheapest gate first, needs no
  image"; the latter is Git-only). Routing them through the container would
  force a python-env build at the top of the guard job on every fresh runner.
- already-`$(TEST_RUN)`/`$(DOCKER_RUN)`-wrapped seams (`validate`,
  `update_trending`, `data-gaps` report) — must NOT be rewrapped (no
  docker-in-docker).

## Proof

- One Makefile seam block documents the host-only exceptions next to `PYTHON_RUN`.
- `tests/test_workflows.py` (extended `test_python_env_seam_...`) asserts each of
  the 5 migrated targets carries `python-env-image` + `$(PYTHON_RUN) ... pure
  command`, and that the host-only exceptions (`openspec-archive-check`,
  `check-commit-authorship`, `file-findings`, `verify-closure`) gain NO
  `$(PYTHON_RUN)` prefix.
- Migrated targets run green through the container on a Docker host.
- Full `make test` exit 0; `make openspec-check` green; `make lint-fix` last.
