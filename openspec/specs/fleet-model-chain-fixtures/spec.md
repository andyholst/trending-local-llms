# fleet-model-chain-fixtures Specification

## Purpose
TBD - created by archiving change free-model-refresh-fixtures-1744. Update Purpose after archive.

## Requirements

### Requirement: Fleet free-tier fixtures are derived from the shipped chain

The three fleet guard modules SHALL derive every free id, alias and context value from `agents/model_chain.json` at test time through one shared helper. No frozen catalogue literal SHALL remain in those modules. A live refresh that retires, adds or re-contexts a free model SHALL NOT turn a guard red while the seam under test stays correct.

#### Scenario: A keeper refresh retires the frozen primary

- **Given** a chain whose free primary and one fallback were retired by the weekly refresh
- **When** the three guard modules run against that chain
- **Then** all three finish green, deriving the retired model, successor and context from the chain
- **Test:** tests/test_free_model_refresh.py::test_a_retired_free_model_drops_and_a_retired_primary_hands_over

#### Scenario: The rendered config's primary needle follows the chain

- **Given** a shipped chain whose primary changed from the catalogued snapshot
- **When** a hand-edited lane config replaces the primary with a paid model
- **Then** the gate names the derived primary and the paid model on the edited line
- **Test:** tests/test_agent_model_chain.py::test_a_hand_edited_lane_config_is_refused_and_names_the_lane_and_line

### Requirement: The fixtures follow synthetic data and not a frozen snapshot

A guard SHALL fail on the old frozen shape and pass on the fixed one: a synthetic chain whose ids and aliases are absent from every old literal drives every fixture, and the shipped fixture SHALL equal the shipped chain's free steps.

#### Scenario: A synthetic chain drives all fixtures

- **Given** a synthetic chain with fresh free ids, aliases and contexts absent from the frozen literals
- **When** the derivation helper is called for free steps, primary, alias order and fallback order
- **Then** each result equals the synthetic chain's own values, and the shipped fixture equals the shipped chain's free steps
- **Test:** tests/test_free_model_refresh.py::test_fixtures_follow_the_chain_not_a_frozen_catalogue

#### Scenario: A drifted config is still refused from derived data

- **Given** a rendered lane config whose derived `default:` primary is replaced by a paid model
- **When** provisioning runs
- **Then** the drift is refused and the live profile home stays empty
- **Test:** tests/test_agent_profile_provision.py::test_a_lane_config_that_drifted_from_the_chain_is_refused_not_copied

### Requirement: Fleet local-tier fixtures are derived from the shipped chain

The fleet guard modules SHALL derive every credential-less local-tier needle — the bare server model id, its alias, its own provider and endpoint, and the paid `last_resort` alias that bounds the local alias block — from `agents/model_chain.json` at test time through the shared `tests/fleet_chain_fixtures.py` seam. No frozen local-tier literal SHALL remain in those guards. A legitimate refresh that swaps the local model, its alias, its provider or its endpoint SHALL NOT turn a guard red while the seam under test stays correct.

#### Scenario: The rendered local alias block follows a changed local tier

- **Given** a shipped chain whose local tier names a new bare model id, alias, provider and endpoint
- **When** the rendered-config guard inspects the local fallback entry and the local alias block
- **Then** every needle it asserts is derived from the chain, and the local tier is still the sole credential-less step between the free fallbacks and the paid pin
- **Test:** tests/test_agent_model_chain.py::test_the_rendered_config_carries_the_runtime_fallback_order_and_a_credential_less_local_alias

#### Scenario: A provisioned profile keeps the derived local tier

- **Given** a lane profile home holding a stale config
- **When** provisioning copies the chain-rendered config into it
- **Then** the destination contains the chain's derived local model as a credential-less step and no frozen local id is asserted
- **Test:** tests/test_agent_profile_provision.py::test_a_lane_config_copies_into_the_profile_home_and_the_prior_file_is_kept

### Requirement: The local-tier fixtures follow synthetic data and not a frozen snapshot

A guard SHALL fail on the old frozen shape and pass on the fixed one: a synthetic chain whose local model, alias, provider and endpoint appear in no old literal drives every local-tier fixture, and the shipped derived needles SHALL be present in the rendered config.

#### Scenario: A synthetic local tier drives every local fixture

- **Given** a synthetic chain with a local model, alias, provider and endpoint absent from every frozen literal
- **When** the derivation helpers are called for the local model, alias, provider, endpoint and paid alias
- **Then** each result equals the synthetic chain's own values, and the shipped derived needles are present in the rendered config
- **Test:** tests/test_agent_model_chain.py::test_local_tier_fixtures_follow_the_chain_not_a_frozen_snapshot

#### Scenario: A local tier naming a provider/model id is still refused

- **Given** a chain whose local step names a provider-qualified model instead of a bare server id
- **When** the chain gate checks the local tier
- **Then** the shape is refused with a `[model-chain] FAIL` line, independent of any fixture value
- **Test:** tests/test_agent_model_chain.py::test_the_local_tier_is_guarded_like_every_other_tier
