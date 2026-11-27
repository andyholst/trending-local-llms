## ADDED Requirements

### Requirement: The rendered lane config pins goal_judge to the served local id

The chain SHALL declare `auxiliary.goal_judge` by chain alias. The renderer SHALL emit, into every
generated `agents/tll-*/config.yaml`, an `auxiliary.goal_judge` block whose provider, model and
base_url are those of the chain's OWN `role=local_fallback` entry, followed by a `fallback_chain`
built from the declared Nous fallback aliases in chain order. No rendered judge step SHALL carry a
credential value or a `key_env`.

#### Scenario: Every rendered lane config carries the served judge pin

- **Given** the shipped chain whose `role=local_fallback` entry names the id the local server serves
- **When** `make agent-profile-model-render` renders the fleet lane configs
- **Then** every `agents/tll-*/config.yaml` carries `auxiliary.goal_judge` with that provider, that
  model and that base_url, and no `key_env`/credential value in the block
- **Test:** tests/test_agent_model_chain.py::test_rendered_lane_configs_pin_goal_judge_to_the_served_local_model

#### Scenario: The judge falls through Nous steps only

- **Given** the shipped chain's fallback aliases
- **When** the rendered config's `auxiliary.goal_judge.fallback_chain` is read
- **Then** it lists exactly the Nous steps in chain order, never the primary and never the served
  local model, and every step is `provider: nous` with no `base_url`/`key_env`
- **Test:** tests/test_agent_model_chain.py::test_goal_judge_fallback_chain_is_only_the_nous_steps

### Requirement: A misrouted judge is refused

`make agent-model-chain-check` SHALL refuse a chain whose `auxiliary.goal_judge.alias` does not name
its own `role=local_fallback` entry, whose fallback list is empty, whose fallback names the primary,
or whose fallback is not a Nous step. The refusal SHALL name the defect and issue #1798.

#### Scenario: A judge pinned to the primary is refused

- **Given** a scratch chain whose judge alias is repointed to the primary step
- **When** `make agent-model-chain-check` runs on that tree
- **Then** it exits 1, names the misrouted `goal_judge`, names #1798, and writes no config

- **Test:** tests/test_agent_model_chain.py::test_a_misrouted_goal_judge_is_refused_by_the_gate

### Requirement: The auxiliary block is owned by the chain

`auxiliary` SHALL be an owned top-level block in both the renderer's append guard and the profile
provision merge, so a declared lane append may not redeclare it and a non-lane profile provision
replaces it with the rendered one while keeping every other block byte-for-byte.

#### Scenario: A non-lane provision replaces the auxiliary block

- **Given** a non-lane profile home carrying a stale `auxiliary:` block and other non-owned blocks
- **When** `make agent-profile-provision PROFILE=<name>` merges the rendered chain
- **Then** the `auxiliary:` block equals the chain's rendered block, every other block is
  byte-identical, and a second provision changes no byte

- **Test:** tests/test_agent_profile_provision.py::test_a_non_lane_profile_merges_only_the_owned_blocks_and_keeps_every_other_byte
