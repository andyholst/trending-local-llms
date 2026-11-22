## ADDED Requirements

### Requirement: The all-profiles sweep ignores hidden directories

`collect_targets()` SHALL exclude every child directory whose name starts with
`.` when enumerating `--all-profiles`, leaving those directories byte-for-byte
untouched and not reporting them as bad profile names.

#### Scenario: A retired dot-directory no longer blocks the sweep

- **Given** a profiles home with one live profile and a `.deleted/` directory
  holding a retired profile config
- **When** `agent_aux_local_sync.py --all-profiles` runs against that home
- **Then** it exits 0, the live profile is synced, the hidden home is unchanged,
  and no output mentions the hidden name
- **Test:** tests/test_agent_aux_local_sync.py::test_all_profiles_skips_hidden_directories_but_explicit_hidden_name_still_refused

#### Scenario: An explicit hidden name is still refused

- **Given** the same scratch home with a `.deleted/` directory
- **When** the operator runs `--profile .deleted` explicitly
- **Then** the seam exits 2 with `not a profile name` and writes nothing
- **Test:** tests/test_agent_aux_local_sync.py::test_all_profiles_skips_hidden_directories_but_explicit_hidden_name_still_refused

### Requirement: The guard is part of the wired suite

The new guard SHALL live in the already-wired `tests/test_agent_aux_local_sync.py`
module and execute in its standalone runner, so `make test` covers it on PR and
push without a new script, target or schedule.

#### Scenario: The standalone runner executes the hidden-directory guard

- **Given** a caller runs `python3 tests/test_agent_aux_local_sync.py`
- **When** the runner walks its test list
- **Then** the hidden-directory guard is called and contributes to the printed
  totals
- **Test:** tests/test_agent_aux_local_sync.py::test_all_profiles_skips_hidden_directories_but_explicit_hidden_name_still_refused
