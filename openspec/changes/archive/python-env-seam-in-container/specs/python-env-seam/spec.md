## ADDED Requirements

### Requirement: The seam forks inside a container

The ONE `PYTHON_RUN` assignment SHALL carry an `$(if $(IN_CONTAINER),…)` fork. When the
make runs inside a container (`/.dockerenv` present, or `IN_CONTAINER=1`), expanding a
routed target SHALL emit neither `docker run` nor the image-ensure step, and SHALL keep
the pure `python3 scripts/…` command.

#### Scenario: An in-container dry-run

- **Given** a routed target expanded with `IN_CONTAINER=1`
- **When** `make -n pr-body ISSUE=<n>` runs
- **Then** no `docker run` and no `ensure_image.py ensure-python` appears, and the pure
  composer command remains
- **Test:** tests/test_python_env_in_container.py::test_the_seam_expands_differently_inside_a_container

### Requirement: The host path is unchanged

With `IN_CONTAINER` empty, expanding the same routed target SHALL still name the pinned
`trending-local-llms-python-env:latest` harness and the image-ensure step.

#### Scenario: A host dry-run

- **Given** a routed target expanded with `IN_CONTAINER=` (explicitly empty)
- **When** `make -n pr-body ISSUE=<n>` runs
- **Then** the `docker run` harness, the ensure step and the pure command all appear
- **Test:** tests/test_python_env_in_container.py::test_the_seam_expands_differently_inside_a_container

### Requirement: The in-container escape is silent

Inside a container the skipped `python-env-image` ensure SHALL write nothing to stdout,
so a prerequisite can never land in a redirected PR body.

#### Scenario: The skipped ensure

- **Given** `IN_CONTAINER=1`
- **When** `make python-env-image` runs
- **Then** it exits 0 and stdout is empty
- **Test:** tests/test_python_env_in_container.py::test_the_escape_branch_is_silent

### Requirement: The forced branch runs the real recipe

With `IN_CONTAINER=1`, the routed targets SHALL execute the REAL recipe against the
container's own interpreter — not a stand-in — producing the composer's exact output.

#### Scenario: Forced execution

- **Given** `IN_CONTAINER=1` and a fixture issue
- **When** `make pr-body ISSUE=<fixture>` and `make pr-title ISSUE=<fixture>` run
- **Then** each exits 0 and its stdout is byte-equal to `pr_body.render(...)` / `pr_body.title(...)`
- **Test:** tests/test_pr_body.py::test_the_forced_in_container_branch_runs_the_real_recipe

### Requirement: The three composers route through the seam

`pr-title`, `pr-body` and `architecture-pr-body` SHALL each declare `python-env-image`
and run a pure `$(PYTHON_RUN) python3 scripts/pr_body.py …` command; `refresh-pr-body`
SHALL stay host-only.

#### Scenario: The routing map

- **Given** the Makefile
- **When** it is read
- **Then** each of the three targets carries the seam prefix and the pure command
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

### Requirement: The description no longer calls the composers host targets

`ARCHITECTURE.md` SHALL NOT claim that `pr-body` runs on the runner's own `python3`, nor
that `architecture-pr-body` is a host target.

#### Scenario: The prose rows

- **Given** the diff
- **When** `ARCHITECTURE.md` is read
- **Then** no row makes either stale claim, and the `pr-body` row names the seam
- **Test:** tests/test_python_env_in_container.py::test_the_description_no_longer_calls_the_composers_host_targets
