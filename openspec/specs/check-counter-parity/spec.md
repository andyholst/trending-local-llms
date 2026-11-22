# check-counter-parity Specification

## Purpose
TBD - created by archiving change check-counter-parity-1301. Update Purpose after archive.

## Requirements

### Requirement: Plain pytest cannot out-green the script seam

A plain `pytest` run over the repository's test modules SHALL produce a red session when any collected module's own failure counter is non-zero, naming that module. The verdict of `pytest` and the verdict of `scripts/run_tests.sh` SHALL NOT be able to disagree on the same bytes.

#### Scenario: A module whose check() fails under plain pytest

- **Given** a test module with a `check()` counter and a `test_*` function whose `check()` call fails
- **When** plain `pytest` collects and runs that module
- **Then** the session exits non-zero and the output names the module and its counter value
- **Test:** tests/test_check_counter_parity.py::test_the_plugin_fails_the_session_on_a_failing_counter

#### Scenario: A clean module stays green

- **Given** a test module whose `check()` calls all pass
- **When** plain `pytest` runs it
- **Then** the session exits zero and the parity report names no failing module
- **Test:** tests/test_check_counter_parity.py::test_the_plugin_is_a_no_op_on_a_clean_module

#### Scenario: The same bytes as a script

- **Given** the planted failing module
- **When** it is run as a script (`python3 <module>.py`)
- **Then** it exits non-zero, so the pytest verdict and the seam verdict agree
- **Test:** tests/test_check_counter_parity.py::test_the_plugin_fails_the_session_on_a_failing_counter

### Requirement: Every check()-counter module is observable

The parity detector SHALL recognise every module-level failure counter the tree actually declares, and `make check-counter-parity` SHALL FAIL when a module defines `check()` but declares no counter the detector can read.

#### Scenario: The tree-wide drift scan

- **Given** the repository's `tests/` tree
- **When** `make check-counter-parity` runs
- **Then** every module defining `check()` is either observed or named as drift, and a drift exits non-zero
- **Test:** tests/test_check_counter_parity.py::test_the_detector_classifies_the_tree

#### Scenario: The counter spellings the tree uses

- **Given** the house `_FAIL = 0`, the chained `PASSED = FAILED = 0`, the typed list `FAILURES: list[str] = []` and a module with no counter
- **When** the detector classifies each text
- **Then** the first three qualify with their counter read and the last does not
- **Test:** tests/test_check_counter_parity.py::test_the_detector_classifies_the_tree

#### Scenario: An unreadable tree

- **Given** a root with no `tests/` directory
- **When** the detector scans it
- **Then** it exits 2 loudly rather than reporting a clean tree
- **Test:** tests/test_check_counter_parity.py::test_the_detector_classifies_the_tree

### Requirement: The seam is registered once and leaves the runner untouched

The parity plugin SHALL be loaded through `tests/conftest.py` naming the ONE implementation, and SHALL NOT become a test module of its own.

#### Scenario: The conftest registers the one plugin

- **Given** `tests/conftest.py`
- **When** plain `pytest` runs
- **Then** `check_counter_parity` is loaded as a plugin and no second implementation exists
- **Test:** tests/test_check_counter_parity.py::test_wiring

#### Scenario: The script runner is unchanged

- **Given** `scripts/run_tests.sh` and the Makefile's `_test`
- **When** `make test` runs
- **Then** the runner still globs `test_*.py`, does not collect `conftest.py`, and never imports pytest
- **Test:** tests/test_check_counter_parity.py::test_wiring

#### Scenario: The target is wired into a CI gate

- **Given** the Makefile
- **When** `make lint` runs
- **Then** `check-counter-parity` is called by a target the pipeline runs
- **Test:** tests/test_check_counter_parity.py::test_wiring
