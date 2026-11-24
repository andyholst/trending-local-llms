## ADDED Requirements

### Requirement: The `scrubbed_run` redaction filter runs through the ONE python-env seam

The live redaction filter SHALL run as `$(PYTHON_RUN) python3 scripts/scrub_log.py …` at the redactor end of the pipeline, never as a bare host `python3`. The harness SHALL NOT be wrapped around the command being scrubbed: those agent legs are already `$(DOCKER_RUN)`/`$(TEST_RUN)` containers, so a second wrap would be docker-in-docker. The capture contract (raw + redacted files, `--append` per round, streamed masked lines, the command's own status under `pipefail`) SHALL be unchanged.

#### Scenario: The macro pipes its stream through the container seam

- **Given** the `scrubbed_run` macro at this change's head
- **When** a caller invokes it
- **Then** the redactor side of the pipeline is `$(PYTHON_RUN) python3 scripts/scrub_log.py --stream …`, and no recipe line pipes a bare `python3 scripts/scrub_log.py`
- **Test:** tests/test_os_agnostic_make.py::test_the_two_cross_cutting_seams_run_through_the_container_seam

#### Scenario: The nine agent-leg targets are not hiding behind an exception

- **Given** the Makefile at this change's head
- **When** the host-only exception list is read
- **Then** `search-nvidia`, `search-metal`, `search-cpu`, `search-amd`, `search`, `fix`, `implement-issue`, `review-issue` and `review-issue-window` are all absent from it
- **Test:** tests/test_os_agnostic_make.py::test_the_two_cross_cutting_seams_run_through_the_container_seam

### Requirement: The parse-time query execs run through the seam

The five parse-time derivations (`query_coverage.py --queries` and `query_vocab.py --print {nvidia,metal,cpu,amd}`) SHALL execute through `$(PYTHON_RUN)`, so expanding a search leg needs the CONTAINER's interpreter rather than the host's. They SHALL stay recursive (`=`), so the seam still starts only when a leg prompt actually reads the list.

#### Scenario: Every parse-time query exec carries the seam

- **Given** the Makefile at this change's head
- **When** the five `$(shell …)` query assignments are read
- **Then** each one runs `$(shell $(PYTHON_RUN) python3 …)`, and none is a bare `$(shell python3 …)`
- **Test:** tests/test_os_agnostic_make.py::test_the_two_cross_cutting_seams_run_through_the_container_seam

#### Scenario: The search credential pre-flight proves the key through the seam

- **Given** `_search-preflight`, which fails loudly when `FIRECRAWL_API_KEY` is missing or empty
- **When** `make search-*` expands it on a host
- **Then** the check runs through `$(PYTHON_RUN)` and the seam forwards the `FIRECRAWL_API_KEY` name, so no host interpreter runs before the agent container
- **Test:** tests/test_os_agnostic_make.py::test_the_two_cross_cutting_seams_run_through_the_container_seam

### Requirement: No public target outside the documented exceptions reaches a bare host interpreter

A guard SHALL read the REAL Makefile and fail when any PUBLIC target reaches a bare host `python3`/`pip`/`uv` — or a bare pip-tools console script (`pip-compile`, `pip-sync`, `pip-tools`; #1593) — through a recipe line, a `$(call …)` macro body, a `$(shell …)` parse-time exec, or one bare `$(MAKE) _x` hop. A line carrying a container harness (`$(PYTHON_RUN)`, `$(TEST_RUN)`, `$(DOCKER_RUN)`, `$(OS_OPTS)`, `docker run`) is clean.

#### Scenario: The real tree is green through the guard's own CLI

- **Given** the Makefile at this change's head
- **When** `scripts/check_no_bare_host_python.py` runs against it
- **Then** it exits 0 and prints its OK verdict, having seen every public target
- **Test:** tests/test_os_agnostic_make.py::test_the_real_tree_has_no_bare_host_invocation_outside_the_exceptions

#### Scenario: The guard is RED on the pre-change seam shapes

- **Given** the pre-change shapes — a bare `python3 scripts/scrub_log.py` inside `scrubbed_run`, and a bare `$(shell python3 …)`
- **When** the detector runs
- **Then** it reports both (the macro body is analysed as its own line, so a harness in the caller's argument cannot launder it), while the SAME shapes containerised are clean
- **Test:** tests/test_os_agnostic_make.py::test_the_detector_is_red_on_the_pre_change_seam_shapes

#### Scenario: The pip-tools console scripts are tokens, and their recipes stay harnessed (#1593)

- **Given** a planted `pip-compile …` and a bare `pip-tools …` in a NON-exception PUBLIC target
- **When** the detector runs
- **Then** both are reported naming the target and line number, while the REAL private `_requirements` / `_generate-requirements` recipes that carry those commands walk to no finding because their only entry is a `$(DOCKER_RUN) make _x` hop
- **Test:** tests/test_os_agnostic_make.py::test_the_detector_sees_the_pip_tools_console_scripts_and_keeps_them_harnessed

### Requirement: The host-only exception list is mechanical and agrees with the docs

The ONE exception list SHALL be `EXCEPTIONS` in `scripts/check_no_bare_host_python.py`, with a reason per target; the SAME names SHALL be mirrored between the Makefile's `HOST-EXCEPTIONS-BEGIN/END` markers. A guard SHALL fail when the two drift or when a documented name is not a real public target, so a new bare invocation cannot land silently and a removed target cannot linger as dead documentation.

#### Scenario: The Makefile mirror and EXCEPTIONS agree exactly

- **Given** the Makefile's `HOST-EXCEPTIONS-BEGIN/END` block and `EXCEPTIONS`
- **When** the agreement check runs
- **Then** the two sets are equal and every documented exception names a real PUBLIC target
- **Test:** tests/test_os_agnostic_make.py::test_the_documented_exception_list_agrees_with_the_scanner

### Requirement: The guard is reachable from `make lint`

The guard SHALL ship usable, not merely present: `make lint` SHALL run it behind a public `check-no-bare-host-python` target, so a red tree fails the cheapest gate instead of only the suite.

#### Scenario: `make lint` runs the guard

- **Given** the `lint` target at this change's head
- **When** its recipe is read
- **Then** it calls `check-no-bare-host-python`, whose public target and script both exist
- **Test:** tests/test_os_agnostic_make.py::test_the_guard_is_wired_into_lint_and_reachable
