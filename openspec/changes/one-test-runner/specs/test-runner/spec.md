# test-runner

## ADDED Requirements

### Requirement: One runner discovers and runs every test module

`make test` MUST run every `tests/test_*.py` through `scripts/run_tests.sh`, which
discovers the modules itself, and MUST NOT keep a dead alternative path (a pytest
invocation whose failure is discarded).

#### Scenario: the makefile names no module and no pytest

- **Given** the repository's `Makefile`
- **When** the wiring guard reads the `_test` recipe
- **Then** it is `bash scripts/run_tests.sh` and the Makefile contains no `python3 -m pytest tests/` invocation
- **Test:** tests/test_ci_wiring.py::test_the_makefile_has_exactly_one_runner_and_no_dead_pytest_branch

#### Scenario: every module on disk is run

- **Given** the repository's `tests/` directory
- **When** `scripts/run_tests.sh --list` runs
- **Then** it prints every `tests/test_*.py` exactly once
- **Test:** tests/test_ci_wiring.py::test_the_runner_lists_every_module

### Requirement: The runner stops at the first red with that module's output

A module that exits non-zero MUST fail the run, its own output MUST be shown, and the
modules after it MUST NOT run.

#### Scenario: the second of three modules fails

- **Given** a tests directory whose second module exits 1
- **When** the runner runs it
- **Then** exit status is 1, the failing module is named with its output, and the third module never runs
- **Test:** tests/test_ci_wiring.py::test_a_failing_module_stops_the_run

#### Scenario: every module passes

- **Given** a tests directory whose modules all exit 0
- **When** the runner runs it
- **Then** exit status is 0 and it reports how many modules ran
- **Test:** tests/test_ci_wiring.py::test_a_green_directory_passes

### Requirement: A run that discovers no test is a failure

A directory with no `test_*.py` MUST fail the run with a message naming what it looked
for, because a suite that runs nothing would otherwise report success.

#### Scenario: the directory holds no test module

- **Given** an empty tests directory
- **When** the runner runs
- **Then** exit status is 1 with a message naming what it looked for
- **Test:** tests/test_ci_wiring.py::test_an_empty_directory_is_a_failure_not_a_vacuous_pass
