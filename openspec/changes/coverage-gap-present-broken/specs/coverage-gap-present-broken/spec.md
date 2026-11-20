# coverage-gap-present-broken

## ADDED Requirements

### Requirement: the coverage-gap seam probes presence only, and a present-but-broken CLI is a real failure

`scripts/coverage_gap.py` exposes `external_binary_usable(binary) -> bool` and the named boundary
`PRESENCE_IS_PRESUMED_USABLE`. `external_binary_gap` declares a half ONLY when a binary is absent;
it never executes a binary to decide coverage.

WHEN a CLI is on PATH and its real invocation fails
THEN the seam declares nothing and the half that drives it goes red with the CLI's own error.

#### Scenario: a present-but-broken CLI declares no gap

- **Given** a real `external_binary_gap` driven in a subprocess whose `PATH` carries a stub `hermes` that exits 1
- **When** the seam probes
- **Then** it returns `""` and prints nothing, and `external_binary_usable("hermes")` is `True`
- **Test:** `tests/test_test_container_identity.py::test_a_present_but_broken_cli_is_a_real_failure_not_a_declared_gap` — real seam, real `shutil.which`

#### Scenario: the half that drives a broken CLI fails loudly

- **Given** the same stub on `PATH`, driving the real `scripts/hermes_skills_register.py`
- **When** it invokes `hermes config get`
- **Then** it exits 2 with the CLI's own failure message and prints no `[coverage-gap]` line
- **Test:** `tests/test_test_container_identity.py::test_a_present_but_broken_cli_is_a_real_failure_not_a_declared_gap` — real register script, real subprocess

#### Scenario: an absent CLI still declares

- **Given** a binary that ships nowhere
- **When** the seam probes
- **Then** it declares the half exactly as before (issue #1154's contract is unchanged)
- **Test:** `tests/test_test_container_identity.py::test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted` — real seam, real runner
