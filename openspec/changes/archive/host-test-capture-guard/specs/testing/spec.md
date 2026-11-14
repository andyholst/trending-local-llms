## ADDED Requirements

### Requirement: Every passing test module leaves a trace in the runner stream

`scripts/run_tests.sh` SHALL print one `[test] ok <module>` line for every
passing module it runs, SHALL NOT dump a passing module's own output into the
stream, and SHALL keep the stop-at-first-red contract: the failing module's
full output is shown and the run ends non-zero.

#### Scenario: A green fixture leaves a per-module trace

- **Given** a fixture `tests/` with two passing modules
- **When** `scripts/run_tests.sh <fixture>` runs
- **Then** stdout holds `[test] ok test_dummy_a.py`, `[test] ok test_dummy_b.py`
  and the final `[test] 2 module(s) passed`, and none of the modules' own chatter
- **Test:** tests/test_test_capture_guard.py::test_a_passing_module_leaves_a_trace_in_the_stream

#### Scenario: The first red still stops the run with its output shown

- **Given** a fixture whose third module exits 1
- **When** `scripts/run_tests.sh <fixture>` runs
- **Then** the two green modules are still traced, the red module's output is
  shown, the run names it FAILED and exits non-zero
- **Test:** tests/test_test_capture_guard.py::test_the_first_red_stops_the_run_and_its_output_is_shown

### Requirement: TEST_RUN unbuffers the container's Python streams

`TEST_RUN` SHALL set `-e PYTHONUNBUFFERED=1` explicitly on the test container,
the same explicit setting `DOCKER_RUN` carries (issue #591), so every
container-side `make`/Python process flushes each line into the host stream.

#### Scenario: The flag is part of the TEST_RUN definition

- **Given** the repository `Makefile`
- **When** the `TEST_RUN :=` body is read
- **Then** it contains `-e PYTHONUNBUFFERED=1` alongside the existing forwards
- **Test:** tests/test_test_capture_guard.py::test_test_run_forwards_the_unbuffered_lesson

### Requirement: `make test` refuses a verdict over an empty capture

The public `test:` target SHALL tee the container stream into a capture file;
if the capture holds no `[test]` line it SHALL print one loud refusal naming
the empty capture (`UNVERIFIABLE`) and exit non-zero regardless of the suite's
rc. When `[test]` lines arrived it SHALL report the number of `[test] ok`
traces and the suite's exit code, keep the suite stream visible on stdout, and
propagate the suite's failure.

#### Scenario: Silence with rc 0 is refused

- **Given** a fixture Makefile whose `TEST_RUN` is a stub that prints nothing
  and exits 0
- **When** `make test` runs the real `test:` recipe text copied from the repo
  Makefile
- **Then** the run exits non-zero and stderr names the empty capture as
  unverifiable
- **Test:** tests/test_test_capture_guard.py::test_an_empty_capture_is_refused_loudly

#### Scenario: A green capture passes and counts its traces

- **Given** a stub printing `[test] ok` lines and the verdict, exit 0
- **When** `make test` runs
- **Then** it exits 0, stdout still shows the suite's verdict, and stderr
  reports the trace count
- **Test:** tests/test_test_capture_guard.py::test_a_green_capture_passes_and_counts_its_traces

#### Scenario: A red suite stays red through the guard

- **Given** a stub printing verdict lines and exiting 7
- **When** `make test` runs
- **Then** the run fails and the harness line announces `suite rc=7`
- **Test:** tests/test_test_capture_guard.py::test_the_suite_exit_code_is_propagated
