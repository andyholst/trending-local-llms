# coverage-gap-announce

## ADDED Requirements

### Requirement: the coverage-gap builders return their line and only announce() prints it

`scripts/coverage_gap.py` splits the act: `declare_gap`, `declare_bypass_gap` and
`external_binary_gap` BUILD a declared-gap line and RETURN it without printing; `announce(line)`
is the seam's only print of a gap line. A gap reaches `scripts/run_tests.sh`'s count only when a
guard explicitly announces it — so a demonstration call cannot leak a phantom gap into the verdict,
and `coverage-gap N declared` names exactly the halves that announced.

#### Scenario: a builder call prints nothing

- **Given** the REAL seam driven in a subprocess whose `PATH` lacks `tll-absent-cli-1173`
- **When** `external_binary_gap`, `declare_gap` and `declare_bypass_gap` are called and their
  return values are named in `repr`
- **Then** every builder returns a line carrying `GAP_PREFIX` and `BYPASS_PHRASE`, and the
  subprocess's own stream contains NO line starting with `GAP_PREFIX` — the builders printed
  nothing
- **Test:** `tests/test_test_container_identity.py::test_the_gap_builders_return_quietly_and_only_announce_prints` — real seam, real subprocess

#### Scenario: announce is what makes a gap visible

- **Given** the same subprocess, calling `announce(external_binary_gap(...))`
- **When** the subprocess's stream is read
- **Then** exactly one `GAP_PREFIX` line appears, naming the guard and the reason
- **Test:** `tests/test_test_container_identity.py::test_the_gap_builders_return_quietly_and_only_announce_prints` — real seam

#### Scenario: a module that calls the builders without announcing declares NOTHING to the runner

- **Given** a scratch tree whose module calls `coverage_gap.declare_gap(...)` twice and
  `coverage_gap.external_binary_gap(...)` for an absent CLI, keeps the returns, and never calls
  `announce`
- **When** the REAL `scripts/run_tests.sh` runs that tree
- **Then** the module stays green and the runner names NO declared gap (its
  `coverage-gap N declared` line never appears) — the phantom class (issue #1173:
  `coverage-gap 2 declared` from two demo calls in a container that declared nothing) is
  structurally impossible
- **Test:** `tests/test_test_container_identity.py::test_a_call_that_never_announced_declares_nothing_to_the_runner` — real runner, real seam

#### Scenario: an announced gap is still counted exactly once

- **Given** a scratch tree whose module announces ONE built line
- **When** the REAL runner runs that tree
- **Then** the module stays green and the verdict names `coverage-gap 1 declared` with that guard
- **Test:** `tests/test_test_container_identity.py::test_a_call_that_never_announced_declares_nothing_to_the_runner` — real runner

#### Scenario: the seam prints the gap prefix exactly once, in announce(), and every real half announces

- **Given** `scripts/coverage_gap.py` and the two real declaration sites in `tests/test_agent_skills.py`
- **When** the seam source and the module sources are read
- **Then** the seam's only `print` of a string carrying `GAP_PREFIX` at build time is inside
  `announce` (the `--gap-prefix` report is not a declaration), and BOTH real halves read as
  `coverage_gap.announce(coverage_gap.declare_…(...))` — the leak sites the issue measured are
  gone from the tree
- **Test:** `tests/test_test_container_identity.py::test_the_seam_prints_gap_lines_only_through_announce_and_the_real_halves_announce` — AST over the real tree
