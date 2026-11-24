## ADDED Requirements

### Requirement: The self-archive guards run through the container seam

`self-archive-snapshot` and `self-archive-guard` SHALL each list `python-env-image` as a prerequisite and run their recipe as a PURE `python3 scripts/…` command behind the ONE `$(PYTHON_RUN)` seam, so a runner with Docker but not the pinned Python/deps gets the same #812 protection as a provisioned host.

#### Scenario: Both targets route through the seam

- **Given** the Makefile at this change's head
- **When** the Slice 4b seeded set is checked
- **Then** each of `self-archive-snapshot` and `self-archive-guard` carries the `python-env-image` prerequisite and a `$(PYTHON_RUN) python3 scripts/self_archive_guard.py …` recipe
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: The migration is locked by a guard that fails without it

- **Given** the pre-change Makefile with the two recipes still bare HOST `python3`
- **When** the Slice 4b assertion runs against it
- **Then** it fails, naming the targets that lost the seam
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

### Requirement: The seam exposes the git common dir and the fix-loop baseline

`PYTHON_RUN` SHALL carry the same `GIT_COMMON_DIR` mount as `TEST_RUN`, and SHALL conditionally forward the fix-loop's host baseline directory and `SELF_ARCHIVE_*` variables, so a worktree's real git dir and the baseline file are visible inside the container — otherwise the routed guard would be blind or wrong.

#### Scenario: The git common dir is mounted

- **Given** a worktree whose gitdir lives outside `$PWD`
- **When** the Slice 4b seam assertion reads the `PYTHON_RUN` definition
- **Then** it carries `-v "$(GIT_COMMON_DIR):$(GIT_COMMON_DIR)"`, matching `TEST_RUN`
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: The fix-loop baseline path and env are forwarded

- **Given** `SELF_ARCHIVE_BASELINE` set by `scripts/fix_loop.sh`
- **When** the Slice 4b seam assertion reads the `PYTHON_RUN` definition
- **Then** it mounts `$(dir $(SELF_ARCHIVE_BASELINE))` and forwards `SELF_ARCHIVE_BASELINE`, `SELF_ARCHIVE_REF` and `SELF_ARCHIVE_RESTORE`, while a host without the fix-loop env gets no extra mount
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

### Requirement: Real-repository behavior is preserved through the container

Because each recipe stays a PURE `python3 scripts/…` command, the guard's snapshot/check/restore behavior on a real git repository SHALL be identical to the host path; the seam change alone must not weaken the #812 protection.

#### Scenario: A clean tree stays green through the seam

- **Given** a real git checkout with baseline-active changes intact
- **When** the container-routed snapshot then check run
- **Then** the baseline is written to the host path and the check is green
- **Test:** tests/test_self_archive_guard.py::test_snapshot_then_check_on_a_clean_tree_is_green

#### Scenario: A mid-run archive move is still detected and restored

- **Given** a baseline-active change moved into the archive mid-run
- **When** the container-routed guard runs with `SELF_ARCHIVE_RESTORE=1`
- **Then** it reports the dismantle, moves the change back and stays red
- **Test:** tests/test_self_archive_guard.py::test_a_move_into_the_archive_is_reported_and_restored

#### Scenario: The in-container seam fork is unchanged

- **Given** `IN_CONTAINER=1` (no docker inside the test image)
- **When** the real `make` is dry-run for a routed recipe
- **Then** the docker harness and image-ensure disappear while the pure command remains
- **Test:** tests/test_python_env_in_container.py::test_the_seam_expands_differently_inside_a_container
