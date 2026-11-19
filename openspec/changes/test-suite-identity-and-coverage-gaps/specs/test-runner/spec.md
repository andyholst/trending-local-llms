# test-runner

## ADDED Requirements

### Requirement: The suite names the identity that measured it

`scripts/run_tests.sh` — reached from `make test` only through `_test:` (rule 6m) —
MUST print one identity line before any verdict, built by `scripts/coverage_gap.py`
(`identity_line()`), naming the uid/gid the suite ran under, the uid:gid that invoked
it when that was forwarded to it, and whether the process ran as the invoking uid or
as an image's default user. `make test` MUST refuse a capture that carries the suite's
verdict lines but no identity line: an rc 0 over a suite that never said who measured
it cannot tell a full suite from a suite whose permission plants were walked through
by a privileged uid. The identity line is a report, not a failure — it never changes
the suite's exit code.

#### Scenario: a runner run states whose uid measured it

- **Given** a fixture tests dir holding one green module
- **When** `bash scripts/run_tests.sh <scratch>` runs over it with an invoking
  `uid:gid` forwarded
- **Then** the output carries the seam's identity line naming
  `container uid=<the real uid>` and `invoking uid=<the forwarded pair>` with
  `run-as=invoking uid`, and the run still exits 0
- **Test:** tests/test_test_container_identity.py::test_the_runner_names_the_identity_it_measured

#### Scenario: a container identity that is NOT the invoker is stated, not inferred

- **Given** `scripts/coverage_gap.py --identity-line` invoked with a forwarded
  invoking `uid:gid` that is not the process's own
- **When** the seam renders the line
- **Then** the line says `run-as=image default user, NOT the invoking uid` instead of
  claiming the invoker's identity, and with nothing forwarded it says
  `invoking uid=unset` rather than guessing
- **Test:** tests/test_test_container_identity.py::test_the_identity_line_distinguishes_a_container_uid_from_the_invoker

#### Scenario: `make test` refuses a capture that never named its identity

- **Given** the REAL `test:` recipe extracted from the repository's `Makefile`, run
  through `make -f <fixture Makefile> test` with the container replaced by a PATH
  stub that streams `[test] ok …` plus the pass verdict and exits 0, but streams no
  identity line (the shape measured on the host after issue #1145 landed)
- **When** the recipe finishes
- **Then** `make` fails, and the refusal names the missing suite identity line and
  issue #1147 rather than reporting a green suite
- **Test:** tests/test_test_container_identity.py::test_make_test_refuses_a_capture_that_never_named_its_identity

### Requirement: A guard that could not run declares its coverage gap through ONE seam

`scripts/coverage_gap.py` holds the ONLY definition of the gap prefix
(`[coverage-gap]`), the bypass phrase and the identity prefix; a guard declares a gap
through `declare_gap`/`declare_bypass_gap`, and `scripts/run_tests.sh` reads all three
strings from that seam (a seam it cannot read exits 2, naming the seam, never a silent
green). The runner scans every module's output — a passing module's output included,
which the runner used to delete unread — and (a) reports each declared gap in its
verdict (`[harness] coverage-gap <N> declared …`, naming which guard did not run), and
(b) FAILS the run when a module emits the bypass phrase outside a declared gap, naming
the module, the issue and the fix ("report it through `scripts/coverage_gap.py`, never
as a bare SKIP"). A declared gap is honest coverage information and MUST NOT turn the
suite red; an undeclared bypass MUST NOT stay green.

#### Scenario: a declared gap in a PASSING module reaches the verdict

- **Given** a fixture dir holding a green module and a green module that calls
  `coverage_gap.declare_bypass_gap(...)`
- **When** `bash scripts/run_tests.sh <scratch>` runs over it
- **Then** the run exits 0, the verdict prints `[harness] coverage-gap 1 declared`, and
  the report names the guard that did not run — proving the passing module's output was
  read before it was deleted
- **Test:** tests/test_test_container_identity.py::test_a_declared_gap_in_a_GREEN_module_reaches_the_verdict

#### Scenario: a bypass that never declared its gap turns the runner red

- **Given** a fixture dir holding a module that prints the seam's bypass phrase as a
  bare `SKIP` and exits 0 (the shape `tests/test_agent_skills.py` printed in CI run
  44551541279), the phrase obtained from `coverage_gap.py --phrase` rather than spelled
  in the test
- **When** the runner finishes
- **Then** the runner exits 1, naming the module, issue #1147 and the declared seam the
  bypass should have travelled through, and it still prints its own verdict line
- **Test:** tests/test_test_container_identity.py::test_a_bypass_that_never_declared_its_gap_turns_the_runner_red

#### Scenario: a declared line and a bare line in one module are separated

- **Given** a module that declares one gap through the seam and prints a second bypass
  as a bare `SKIP`
- **When** the runner finishes
- **Then** the run exits 1 for the undeclared half only, and the refusal does not name
  the declared half — the seam prefix, not the wording, decides which half is honest
- **Test:** tests/test_test_container_identity.py::test_a_declared_and_an_undeclared_line_in_one_module_are_separated

#### Scenario: the runner reads the strings from the seam and never re-spells them

- **Given** the text of `scripts/run_tests.sh` and `scripts/docker_test_run.sh`
- **When** the guard inspects them
- **Then** both call the seam (`--gap-prefix`, `--phrase`, `--identity-line`), neither
  contains the bypass phrase or the gap prefix as a literal, and `coverage_gap.py`
  defines each string exactly once; and a runner whose seam script is missing exits 2
  naming the seam instead of passing vacuously
- **Test:** tests/test_test_container_identity.py::test_the_runner_reads_the_phrases_from_the_seam_and_never_spells_them
  and tests/test_test_container_identity.py::test_the_runner_refuses_loudly_when_the_seam_script_is_gone

#### Scenario: `make test` counts the declared gaps it captured

- **Given** the REAL `test:` recipe over a PATH-stub container that streams the identity
  line, a `[harness] coverage-gap 1 declared …` verdict line and the gap itself, and
  exits 0
- **When** `make -f <fixture Makefile> test` runs
- **Then** `make` exits 0, its harness verdict announces the declared coverage-gap
  report it captured, and the suite's own identity and gap lines stay visible in the
  stream
- **Test:** tests/test_test_container_identity.py::test_make_test_reports_declared_coverage_gaps_in_its_own_verdict

#### Scenario: a guard that bypasses reports through the seam, not as a bare SKIP

- **Given** `tests/test_agent_skills.py`'s teardown permission half
- **When** its source is read
- **Then** it declares the bypass via `coverage_gap.declare_bypass_gap(`, prints no bare
  `SKIP` bypass line and re-spells no seam string, and it still states the
  always-checked half that keeps the teardown contract locked
- **Test:** tests/test_test_container_identity.py::test_the_permission_half_guard_reports_through_the_seam_not_as_a_bare_skip
