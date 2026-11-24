## ADDED Requirements

### Requirement: Owner-authorized lane settings are rendered from the tree

The fleet chain renderer SHALL render each lane's `config.yaml` as the byte-exact chain output plus
that lane's OPTIONAL declared `config.append.yaml`, and SHALL refuse an append that redeclares a
chain-owned block (`model:`, `model_aliases:`, `fallback_providers:`). A lane with no append file SHALL
render exactly as before.

#### Scenario: The #1591 setting renders into the tll-implementer config

- **Given** `agents/tll-implementer/config.append.yaml` declares `security.protected_instruction_files: false`
- **When** `make agent-profile-model-render` runs
- **Then** that lane's `config.yaml` carries the block after an unchanged rendered chain, and no other lane's config carries it
- **Test:** tests/test_agent_model_chain.py::test_a_declared_lane_append_is_rendered_and_an_undeclared_one_is_refused

#### Scenario: An undeclared or chain-owned extra is refused

- **Given** a lane config with a hand-added block, or an append redeclaring `model:`
- **When** `make agent-model-chain-check` runs
- **Then** it exits non-zero and names the drift or the redeclared block
- **Test:** tests/test_agent_model_chain.py::test_a_declared_lane_append_is_rendered_and_an_undeclared_one_is_refused

### Requirement: A whole-copy re-provision preserves declared settings

Provisioning a lane SHALL install exactly `render_lane`'s bytes and SHALL report that home CLEAN in
`CHECK=1`; a non-lane merge home SHALL keep the plain chain render.

#### Scenario: Re-provision tll-implementer

- **Given** a profile home holding the old rendered config and the declared #1591 append in the tree
- **When** the lane is provisioned
- **Then** the installed config still carries `security.protected_instruction_files: false`, matches the rendered lane config byte-for-byte, and `CHECK=1` answers CLEAN
- **Test:** tests/test_agent_profile_provision.py::test_a_declared_lane_append_survives_a_whole_copy_reprovision

### Requirement: Host-ahead skill notes are landed without host noise

The five reconciled lane `SKILL.md` mirrors SHALL carry the legitimate host-ahead lessons with their
issue references, SHALL NOT carry host-state claims that contradict the measured host, and SHALL keep
master's canonical bullets; the union SHALL add no duplicate line or clause.

#### Scenario: The reconciled mirrors pass the union/no-duplicate guard

- **Given** the five reconciled mirrors at this change's head
- **When** `tests/test_fleet_lifecycle.py` runs against the pinned pre-union base
- **Then** no non-trivial line or clause grows its copy count and every pinned needle occurs exactly once
- **Test:** tests/test_fleet_lifecycle.py::test_mirror_unions_add_no_duplicate_or_interleaved_bullets
