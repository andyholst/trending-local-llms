# os-agnostic-make-python-env-seam

## ADDED Requirements

### Requirement: a python-env recipe runs inside the python-env container via the PYTHON_RUN seam

The `_command` of a migrated recipe stays a pure call (`python3 scripts/X.py …`),
and the container harness lives in the ONE `PYTHON_RUN` seam, so a host with
Docker but not the pinned Python/deps still runs the target.

WHEN a target migrated through `PYTHON_RUN` is invoked
THEN its recipe `docker run`s into the python-env image with `$$PWD` mounted at `/workspace`
AND it runs as the invoking user (so a write lands owned by the repo owner)
AND the recipe contains no per-recipe docker boilerplate.

#### Scenario: openspec-index runs through the python-env container

- **Given** the `openspec-index` target
- **When** the recipe is read from the Makefile
- **Then** it starts with `$(PYTHON_RUN)` and calls `python3 scripts/openspec_index.py --write`
- **Test:** `tests/test_workflows.py` — asserts `$(PYTHON_RUN) … scripts/openspec_index.py --write`

#### Scenario: architecture-check runs both guard steps through the container

- **Given** the `architecture-check` target
- **When** the recipe is read from the Makefile
- **Then** both its steps start with `$(PYTHON_RUN)` (`architecture_check.py` and `architecture_bot.py --check`)
- **Test:** `tests/test_workflows.py` — asserts both lines route through `$(PYTHON_RUN)`

#### Scenario: the python-env image has its own hash tag and ensure path

- **Given** `scripts/ensure_image.py`
- **When** `tags` is printed
- **Then** it includes `PYTHON_TAG` = sha12(`Dockerfile.python-env` + `requirements.txt`)
- **Test:** `tests/test_ensure_image.py` — `python_hash`/`python_tag` tests

#### Scenario: the python-env image is built locally and never probes the registry

- **Given** `scripts/ensure_image.py` `ensure-python` and a host with no local python-env image
- **When** `make python-env-image` is run
- **Then** it builds from `Dockerfile.python-env` + `requirements.txt`
- **And** it does NOT ask the registry whether the image is published (a never-published package reads `denied`, which issue #235 treats as a loud error)
- **Test:** `tests/test_ensure_image.py` — `ensure-python` never issues `docker manifest inspect`

#### Scenario: a local python-env image is reused, not rebuilt

- **Given** the python-env image is already present locally
- **When** `make python-env-image` is run
- **Then** it reuses the image and builds nothing (no registry round-trip)
- **Test:** `tests/test_ensure_image.py` — `ensure-python` with the local image present issues no `docker build`

### Requirement: the migrated recipe carries no per-recipe docker boilerplate

WHEN a migrated target's recipe is written
THEN the container harness (mount, working dir, user, PYTHONUNBUFFERED) is NOT in the recipe — only the `$(PYTHON_RUN)` prefix
AND `python-env-image` is a prerequisite so the image is ensured before the run.

#### Scenario: the python-env-image ensure target exists and is a prerequisite

- **Given** the `Makefile`
- **When** the migrated targets' prerequisites are read
- **Then** both `openspec-index` and `architecture-check` declare `python-env-image`
- **Test:** `tests/test_workflows.py` — `python-env-image` present + prerequisite wiring

#### Scenario: image-ensure also ensures the python-env image

- **Given** `scripts/ensure_image.py` `ensure` dispatch
- **When** a job that runs the suite calls `make image-ensure`
- **Then** it also ensures the python-env image, so a migrated recipe never starts unprovisioned
- **Test:** `tests/test_ensure_image.py` — `ensure` calls `ensure_python`
