# fleet-model-chain

## ADDED Requirements

### Requirement: The provision seam reports host drift read-only

`scripts/agent_profile_provision.py --check` (`make agent-profile-provision CHECK=1 …`) MUST
compare every named home against the rendered chain and NAME every stale one: a lane home is a
whole copy (its entire config must equal the render), a non-lane home is a merge (only the owned
`model:`/`model_aliases:`/`fallback_providers:` blocks are compared). It MUST exit 1 when any
home drifted, exit 0 `CLEAN` when all match, and exit 2 for a missing home or an unreadable
chain — never a silent pass. It MUST write nothing (no config change, no backup) and MUST NOT
require the credential: a drift report runs on the host whose key is absent. Every existing
write path keeps its credential pre-flight and backup guarantees unchanged.

#### Scenario: stale homes are named, clean homes are not, and nothing is written

- **Given** a scratch profiles root with a stale lane home (whole copy drifted), a stale merge
  home (one owned block drifted, other blocks its own), a clean lane and a clean merge home
- **When** `--check --all --profile developer --profile cleanprofile` runs with NO credential
- **Then** it exits 1, names `STALE lane=tll-tester` and `STALE profile=developer` with the
  drifted block, names no clean home, prints the re-provision remedy, and every file is
  byte-unchanged with no backup created
- **Test:** tests/test_agent_profile_provision.py::test_check_names_every_stale_home_writes_nothing_and_needs_no_credential

#### Scenario: the check is green after provisioning and a missing home is exit 2

- **Given** a scratch profiles root freshly provisioned (lanes + default)
- **When** `--check` runs over the same targets, then over a home that does not exist
- **Then** the first exits 0 `CLEAN`, the second exits 2 naming the missing home
- **Test:** tests/test_agent_profile_provision.py::test_check_is_green_after_provisioning_and_a_missing_home_is_exit_2

#### Scenario: the CHECK=1 seam is wired through the Makefile

- **Given** this repository's Makefile
- **When** the wiring test runs
- **Then** `CHECK ?=` and the `$(if $(CHECK), --check,)` expansion are present beside the
  existing LANE/ALL/PROFILE/PROFILES_HOME wiring
- **Test:** tests/test_agent_profile_provision.py::test_the_target_is_wired_to_the_makefile_and_a_pipeline_job
