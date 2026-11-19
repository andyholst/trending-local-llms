# hermes-temp-home-teardown

## ADDED Requirements

### Requirement: A test's temp Hermes home is removed through the agent's own late-write window

Every test that points Hermes at a temp `HERMES_HOME` MUST remove that home through ONE seam
(`tests/hermes_home.py::remove_hermes_home` / `temp_hermes_home`), not through
`tempfile.TemporaryDirectory`'s single-shot cleanup. Hermes does not stop writing when its CLI
returns: with the pinned 0.23.2 a `hermes config set` seeded `cache/uv/**`, `installs/<hash>` and
`cache/default-plugins.rerun` → `cache/default-plugins.settled` into the home 4 s after the CLI
call had returned (measured on the host), and the plain cleanup raced that pass and died
`OSError: [Errno 39] Directory not empty: '<tmp>/hermes/cache'` — which made `make test` RED in
qa-validate run 44537216542 (`tests/test_agent_skills.py`) with every assertion in the module
already green. A teardown that fails on the agent's own bookkeeping proves nothing.

The seam retries a BOUNDED number of times (40 × 0.25 s) and then raises `AssertionError`: the
retry is for the agent's late writes, never an excuse to swallow an undeletable tree —
`ignore_errors=True` is refused because it launders a real defect into a green suite.

#### Scenario: the registration seam runs the real CLI against a temp home and the module stays green

- **Given** the repository's `scripts/hermes_skills_register.py` and a temp Hermes home created
  through the seam
- **When** the module runs the real `hermes config get/set` calls against it (register, `--check`)
- **Then** every assertion passes and the temp home is removed without an `OSError` escaping the
  module
- **Test:** `tests/test_agent_skills.py::test_setup_registers_the_directory_and_reads_it_back`

#### Scenario: a writer that lands after the caller is done does not defeat the teardown

- **Given** a temp Hermes home whose background seeder is still landing `cache/uv`,
  `installs/<n>` and `cache/default-plugins.settled` while the teardown runs (the writer thread is
  deliberately not joined)
- **When** the seam's teardown removes the home
- **Then** the tree is gone once the context manager exits
- **Test:** `tests/test_agent_skills.py::test_the_temp_home_teardown_survives_a_writer_that_lands_after_the_caller_is_done`

#### Scenario: a home that never becomes removable is a loud failure, not an ignored one

- **Given** a planted temp home whose inner directory cannot be descended (mode `0o000`), so every
  removal attempt fails
- **When** the seam's teardown runs with a small attempt budget
- **Then** it raises `AssertionError` naming the path instead of returning silently
- **Test:** `tests/test_agent_skills.py::test_a_temp_home_that_never_becomes_removable_is_a_loud_failure_not_an_ignored_one`

#### Scenario: every test that points Hermes at a temp home uses the one seam

- **Given** the real Hermes terminal probe (`scripts/agent_shell_keys_check.py`) run against a temp
  `HERMES_HOME`
- **When** the probe group's tests create and release that home
- **Then** they create it through `temp_hermes_home()` (no `tempfile.TemporaryDirectory` around a
  live Hermes home), and the probes stay green
- **Test:** `tests/test_agent_shell_keys.py::test_forced_names_make_every_key_visible`
