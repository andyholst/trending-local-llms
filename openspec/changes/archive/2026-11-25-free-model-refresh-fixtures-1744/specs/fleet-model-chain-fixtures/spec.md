## ADDED Requirements

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
