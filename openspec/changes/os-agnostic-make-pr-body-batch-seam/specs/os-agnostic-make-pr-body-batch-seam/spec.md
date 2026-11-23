# os-agnostic-make-pr-body-batch-seam

## ADDED Requirements

### Requirement: the keeper PR-body/composer recipes run inside the python-env container via the PYTHON_RUN seam

The migrated keeper PR-body recipes stay a pure call (`python3 scripts/X.py …`)
and the container harness lives in the ONE `PYTHON_RUN` seam, so a host with
Docker but not the pinned Python/deps composes the keeper PR bodies.

WHEN a keeper PR-body target is routed through `PYTHON_RUN`
THEN its recipe `docker run`s into the python-env image with `$$PWD` mounted at `/workspace`
AND it runs as the invoking user (so a write lands owned by the repo owner)
AND the recipe contains no per-recipe docker boilerplate (the harness is the macro)
AND `python-env-image` is a prerequisite, so the image is ensured before the run.

#### Scenario: openspec-index-repair-pr-body runs through the python-env container

- **Given** the `openspec-index-repair-pr-body` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/openspec_index_repair.py --print-pr-body …` (pure command), with `python-env-image` a prerequisite
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: openspec-invalid-change-repair-pr-body runs through the python-env container

- **Given** the `openspec-invalid-change-repair-pr-body` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/openspec_invalid_change_repair.py --print-pr-body …` (pure command)
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: architecture-block-repair-pr-body runs through the python-env container

- **Given** the `architecture-block-repair-pr-body` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/architecture_block_repair.py --print-pr-body …` (pure command)
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: the composed keeper body is byte-identical to the host-python output

- **Given** a Docker host with the python-env image built
- **When** each migrated keeper body target runs
- **Then** the composed body equals the host `python3 scripts/X.py --print-pr-body …` output byte for byte
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

### Requirement: the documented host-only PR-body/message targets are NOT routed through the container

Some `python3 scripts/…` targets cannot run in the python-env image: the
`pr-closure.yml` message gates run before any image-ensure, `refresh-pr-body`
composes its window through `gh api` with a host `WINDOW_FILE`, and
`pipeline-failure-ledger-pr-body` reads its `RUN_URL` from the environment
`PYTHON_RUN` does not forward. They must NOT gain a `$(PYTHON_RUN)` prefix; the
seam block documents them so the exception is auditable.

WHEN a PR-body/message target is host-only by design
THEN its recipe keeps a bare `python3 scripts/…` call (no `$(PYTHON_RUN)`)
AND the exception is named in the Makefile seam block next to `PYTHON_RUN`.

#### Scenario: the pr-closure.yml trio and the two env/window-bound composers stay host-side

- **Given** the `pr-message-check`, `issue-message-check`, `commit-message-check`, `refresh-pr-body` and `pipeline-failure-ledger-pr-body` targets
- **When** their recipes are read from the Makefile
- **Then** none of them contains `$(PYTHON_RUN)` in this slice
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container
