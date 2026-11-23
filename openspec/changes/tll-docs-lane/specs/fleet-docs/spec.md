## ADDED Requirements

### Requirement: The docs lane exists as a derived fleet lane

The tree SHALL carry `agents/tll-docs/SOUL.md`, `agents/tll-docs/skills/tll-docs/SKILL.md` and `agents/tll-docs/config.yaml`, and the lane SHALL be discovered by the ONE derivation (`agent_model_chain.fleet_lanes`, every `agents/tll-*/SOUL.md`) so no hand-kept list can omit it.

#### Scenario: The lane is derived from the tree

- **Given** the repository tree with `agents/tll-docs/SOUL.md` present
- **When** `agent_model_chain.fleet_lanes` runs
- **Then** `tll-docs` is in the returned lane set, and `make agent-model-chain-check` renders its config
- **Test:** tests/test_fleet_lifecycle.py::test_the_lane_set_is_derived_and_the_new_lane_is_wired

#### Scenario: The lane config is the chain's own render

- **Given** `agents/model_chain.json` and the tree's lanes
- **When** `make agent-profile-model-render` runs
- **Then** `agents/tll-docs/config.yaml` is byte-identical to what the chain renders, and no credential VALUE appears in it
- **Test:** tests/test_agent_model_chain.py::test_the_shipped_chain_renders_every_lane_config_and_the_gate_is_green

### Requirement: Every lane list carries the new lane

`scripts/fleet_host_sync_check.py`'s `LANES`, `tests/test_fleet_lifecycle.py`, `tests/test_fleet_handover_protocol.py` and `tests/test_host_fleet_souls.py` SHALL list exactly the derived lane set, so a lane the tree derives is never one the host-sync gate skips.

#### Scenario: A lane missing from a list is refused

- **Given** a tree that derives `tll-docs` while a list omits it
- **When** the guard runs
- **Then** it fails naming the list and the missing lane
- **Test:** tests/test_fleet_lifecycle.py::test_the_lane_set_is_derived_and_the_new_lane_is_wired

#### Scenario: The seam's own LANES tuple equals the derived set

- **Given** `scripts/fleet_host_sync_check.py` at this head
- **When** its `LANES` tuple is compared with `agent_model_chain.fleet_lanes`
- **Then** the two sets are equal
- **Test:** tests/test_fleet_lifecycle.py::test_the_lane_set_is_derived_and_the_new_lane_is_wired

### Requirement: The fleet description names the lane

`AGENTS.md` §7b and `agents/README.md` SHALL name `tll-docs` and its remit, and the counted lane number SHALL match the tree.

#### Scenario: The count matches the derived lanes

- **Given** the tree's eight lanes
- **When** `AGENTS.md` §7b is read
- **Then** it says eight lanes and names the `tll-docs` remit
- **Test:** tests/test_fleet_lifecycle.py::test_the_lane_set_is_derived_and_the_new_lane_is_wired

#### Scenario: The host sync gate accepts a host carrying the lane

- **Given** a profile home holding every derived lane's bytes at the fetched base
- **When** `make fleet-host-sync-check` runs
- **Then** it reports eight lanes and exits 0
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
