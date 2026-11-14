# Spec delta: test-harness — host-suite loud skip and full red list (issue #890)

## Added Requirements

### Requirement: The test runner reports every red module in one pass

`scripts/run_tests.sh` SHALL run every discovered `tests/test_*.py` module even
after one has failed, show each failing module's output, and finish with one
summary line naming ALL failed modules. It SHALL exit 1 when any module failed
and 0 when all passed.

#### Scenario: A fixture dir with three red modules reports all three

- **Test:** tests/test_test_runner.py::test_the_runner_reports_every_red_in_one_pass
- **Given** a fixture tests dir with two passing and two failing modules
- **When** `bash scripts/run_tests.sh <dir>` is run once
- **Then** the run exits 1, prints a `=== FAIL:` block for each of the two, and its
  summary line names both failed modules (nothing is hidden behind the first).

#### Scenario: An all-green fixture dir stays green

- **Test:** tests/test_test_runner.py::test_an_all_green_dir_exits_0
- **Given** a fixture tests dir whose modules all exit 0
- **When** the runner is invoked on it
- **Then** it exits 0 and reports the module count passed.

### Requirement: A missing external tool is a loud SKIP, not a traceback

A test module whose gate depends on an external tool that exists only in the
container SHALL check the tool up front and, when it is absent, print a `SKIP:`
line naming the missing tool and exit 0 — never raise `FileNotFoundError`.

#### Scenario: The update-hermes gate without faketime skips loudly

- **Test:** tests/test_test_runner.py::test_the_update_gate_skips_loudly_without_faketime
- **Given** `tests/test_hermes_update_needed.py` run with PATH that cannot resolve
  `faketime`
- **When** the module is executed
- **Then** it exits 0, prints a SKIP naming `faketime`, and prints no traceback.
