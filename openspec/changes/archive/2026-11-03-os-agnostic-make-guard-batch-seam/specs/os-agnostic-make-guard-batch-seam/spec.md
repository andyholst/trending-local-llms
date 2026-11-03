# os-agnostic-make-guard-batch-seam

## ADDED Requirements

### Requirement: the CI-gate guard/validator recipes run inside the python-env container via the PYTHON_RUN seam

The migrated guard recipes stay a pure call (`python3 scripts/X.py …`) and the
container harness lives in the ONE `PYTHON_RUN` seam, so a host with Docker but
not the pinned Python/deps runs the whole guard set — the two Slice-1 proof
targets plus this slice's guard/validator batch.

WHEN a guard/validator target is routed through `PYTHON_RUN`
THEN its recipe `docker run`s into the python-env image with `$$PWD` mounted at `/workspace`
AND it runs as the invoking user (so a write lands owned by the repo owner)
AND the recipe contains no per-recipe docker boilerplate (the harness is the macro)
AND `python-env-image` is a prerequisite, so the image is ensured before the run.

#### Scenario: openspec-tasks-check runs through the python-env container

- **Given** the `openspec-tasks-check` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/check_openspec_tasks.py $(NAME)` (pure command), with `python-env-image` a prerequisite
- **Test:** `tests/test_workflows.py` — the Slice-2 seam assertions (openspec-tasks-check routes)

#### Scenario: openspec-index-check runs through the python-env container

- **Given** the `openspec-index-check` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/openspec_index.py --check` (pure command)
- **Test:** `tests/test_workflows.py` — the Slice-2 seam assertions (openspec-index-check routes)

#### Scenario: findings-check runs through the python-env container (parse-only, no gh)

- **Given** the `findings-check` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/file_findings.py --check` (pure command; `--check` is parse-only and uses no `gh`)
- **Test:** `tests/test_workflows.py` — the Slice-2 seam assertions (findings-check routes)

#### Scenario: check-secret-output runs through the python-env container

- **Given** the `check-secret-output` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/check_secret_output.py check` (pure command)
- **Test:** `tests/test_workflows.py` — the Slice-2 seam assertions (check-secret-output routes)

#### Scenario: query-coverage runs through the python-env container

- **Given** the `query-coverage` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/query_coverage.py …` (pure command, optional `--top`)
- **Test:** `tests/test_workflows.py` — the Slice-2 seam assertions (query-coverage routes)

### Requirement: the host-only (gh-bound / pre-image-ensure) guard targets are NOT routed through the container, and that fact is documented

Some guard/validator `python3 scripts/…` targets need the runner's `gh`/token,
or run before `image-ensure` in qa-validate by design, or are already wrapped in
a `$(TEST_RUN)`/`$(DOCKER_RUN)` seam. They must NOT gain a `$(PYTHON_RUN)`
prefix in this slice; the seam block documents them so the exception is auditable.

WHEN a guard/validator target is host-only by design
THEN its recipe keeps a bare `python3 scripts/…` call (no `$(PYTHON_RUN)`)
AND the exception is named in the Makefile seam block next to `PYTHON_RUN`.

#### Scenario: gh-bound and pre-image-ensure targets stay host-side

- **Given** the `openspec-archive-check`, `check-commit-authorship`, `file-findings`, and `verify-closure` targets
- **When** their recipes are read from the Makefile
- **Then** none of them contains `$(PYTHON_RUN)` in this slice
- **Test:** `tests/test_workflows.py` — the Slice-2 "stays host-only" assertions
