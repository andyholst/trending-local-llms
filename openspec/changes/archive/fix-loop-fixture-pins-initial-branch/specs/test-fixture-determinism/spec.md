# test-fixture-determinism

## ADDED Requirements

### Requirement: scratch git fixtures pin their initial branch, never inherit the host default

Every scratch repository a test fixture creates via `git init` SHALL name its
initial branch explicitly (`-b <branch>`), so the fixture's branch graph is the
same on a host whose `init.defaultBranch` is `main` and on one whose default is
`master`. A fixture that clones from a bare origin it created SHALL find a
non-empty working tree on both hosts.

#### Scenario: the conflicting-base-merge fixture is green on a main-default host

- **GIVEN** a host whose `init.defaultBranch` is `main` (no `[init]` section)
- **WHEN** `python3 tests/test_fix_loop.py` runs the base-merge fixtures
- **THEN** the bare origin's HEAD names `master`, the clone lands a populated
  working tree, and `test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless`
  passes

- **Test:** `tests/test_fix_loop.py::test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless`

#### Scenario: the same fixture is green on a master-default host

- **GIVEN** the same test run with `init.defaultBranch=master` forced in the
  environment
- **WHEN** the module runs
- **THEN** every check passes — the outcome does not depend on the host default

- **Test:** `tests/test_fix_loop.py::test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless`

#### Scenario: an unpinned scratch init is refused by the guard

- **GIVEN** a version of `tests/test_fix_loop.py` whose fixture calls
  `git init` without `-b <branch>` (the pre-fix shape)
- **WHEN** the module's guard test reads the module's own source
- **THEN** the guard fails, naming the unpinned call — the host-default
  dependency cannot creep back silently

- **Test:** `tests/test_fix_loop.py::test_the_scratch_fixtures_pin_their_initial_branch`
