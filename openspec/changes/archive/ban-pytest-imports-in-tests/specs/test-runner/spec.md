# test-runner

## ADDED Requirements

### Requirement: A test module is a standalone script and the lint says so

No test module under `tests/` may `import pytest` (or `from pytest import …`) or call the
`pytest.` API, and `make lint` MUST run a guard that refuses such a module, naming the file and
the line and stating the standalone-script convention with the house pattern
(`tmp_path=None` fallback, explicit `main()`).

#### Scenario: a planted import pytest reaches the guard

- **Given** a tests directory whose module carries a top-level `import pytest`
- **When** `scripts/check_pytest_imports.py` runs it
- **Then** the guard exits 1 naming that file and line and states the house pattern
- **Test:** tests/test_pytest_import_guard.py::test_a_planted_import_pytest_goes_red

#### Scenario: the other pytest spellings

- **Given** fixtures carrying `from pytest import mark` and a `pytest.mark.parametrize` decorator
- **When** the guard runs each
- **Then** each exits 1 naming the fixture
- **Test:** tests/test_pytest_import_guard.py::test_the_other_pytest_spellings_go_red

#### Scenario: a clean tests tree passes

- **Given** a fixture module using only stdlib plus a whole-line comment that mentions pytest
- **When** the guard runs
- **Then** exit status is 0 and the module is not named
- **Test:** tests/test_pytest_import_guard.py::test_a_clean_module_and_a_comment_line_pass

#### Scenario: the real suite is green under its own guard

- **Given** the repository's `tests/` directory
- **When** the guard runs against it
- **Then** exit status is 0 (the guard does not refuse the suite it guards)
- **Test:** tests/test_pytest_import_guard.py::test_the_real_tests_pass_the_guard

#### Scenario: lint runs the guard

- **Given** the repository's `Makefile`
- **When** the wiring test reads the `lint` recipe and the target list
- **Then** `lint` calls `check-pytest-imports` and the target calls the script
- **Test:** tests/test_pytest_import_guard.py::test_lint_runs_the_guard
