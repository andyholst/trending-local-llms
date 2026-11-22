## ADDED Requirements

### Requirement: The fetched-base sync check covers the default profile's owned blocks

`make fleet-host-sync-check` SHALL, beside the seven lane homes, render the model chain at the FETCHED BASE and compare the default profile's owned blocks (`model`, `model_aliases`, `fallback_providers`) against that render. The comparison SHALL use `agent_profile_provision.check_one` with `whole_copy=False` — the ONE drift verdict — and a drifted block SHALL FAIL naming `profile=default` and the field.

#### Scenario: A synced default profile passes

- **Given** a profile home whose `config.yaml` owned blocks equal the base chain's render
- **When** `make fleet-host-sync-check --base <fetched>` runs
- **Then** it exits 0 and reports the default profile as checked
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home

#### Scenario: A drifted owned block is refused

- **Given** a default profile whose `model:` (or `fallback_providers:`) block differs from the base chain's render
- **When** the sync check runs
- **Then** it exits 1 naming `profile=default` and the drifted field
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_refuses_a_diverged_default_profile

#### Scenario: The chain is read at the BASE, never the working tree

- **Given** a working tree whose `agents/model_chain.json` differs from the fetched base
- **When** the sync check renders the chain
- **Then** the render is the base's, so local unmerged work cannot launder a stale host
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_refuses_a_diverged_default_profile

### Requirement: An absent default profile is named, never silently passed

A default profile home that does not exist is not a divergence — CI proves the lane bytes
against `PROFILES_HOME=agents`, which has no parent `config.yaml` — but it SHALL be reported
by name, so a host with a deleted config cannot read as a clean check.

#### Scenario: No default profile home

- **Given** a profile home with no parent `config.yaml`
- **When** the sync check runs
- **Then** it exits 0 and prints a named `SKIP` line for the absent default profile
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_names_an_absent_default_profile
