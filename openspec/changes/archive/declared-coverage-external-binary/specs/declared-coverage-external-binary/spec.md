# declared-coverage-external-binary

## ADDED Requirements

### Requirement: a half that needs an external binary is declared through the coverage-gap seam

`scripts/coverage_gap.py` exposes `external_binary_gap(guard, binary, why)`, returning the ONE
declared-gap line for a guard whose half needs an external binary the current identity does
not have. The line starts with `GAP_PREFIX` (so the runner counts it as a DECLARED gap, keeps
the module green and names it in `[harness] coverage-gap N declared`) and carries
`BYPASS_PHRASE` (so a bare `SKIP` without the seam stays a refusal).

WHEN a module's guard needs a binary that is not on `PATH`
THEN the module declares the half through this seam and exits green,
AND the runner's verdict names the guard that did not run,
AND a module that prints a bare skip instead is still refused.

#### Scenario: the declared line is counted and the module stays green

- **Given** a scratch tests dir holding a green module and a module that calls `coverage_gap.external_binary_gap(...)`
- **When** `scripts/run_tests.sh` runs over that dir
- **Then** the runner exits 0, prints `[harness] coverage-gap 1 declared`, and names the guard
- **Test:** `tests/test_test_container_identity.py::test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted` — real runner

#### Scenario: the real skills module stays green with the CLI absent

- **Given** the repository's `tests/test_agent_skills.py`, run with every `PATH` entry holding a `hermes` executable removed
- **When** the module runs
- **Then** it exits 0 and its output carries the `GAP_PREFIX` line naming `hermes-skills register half`, instead of the CLI's own "not on PATH" failure and a `FileNotFoundError`
- **Test:** `tests/test_test_container_identity.py::test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted` — real module, real PATH

#### Scenario: the Makefile-wiring checks still run without the CLI

- **Given** the same module with the CLI absent
- **When** it runs
- **Then** the `setup:` wiring checks (the `_hermes-skills-register` / `_hermes-skills-check` recipe) still execute before the declared half returns
- **Test:** `tests/test_agent_skills.py::test_setup_registers_the_directory_and_reads_it_back` — real module
