# fleet-model-chain

## ADDED Requirements

### Requirement: Free-tier test fixtures derive from the shipped chain, not a snapshot

The tests that exercise the fleet model chain and the weekly free-tier refresh MUST read their
free ids, context windows, primary id and retirement alias from `agents/model_chain.json` at test
time. They MUST NOT spell a currently-shipped free id as a literal fixture: a live catalogue
refresh changes that set, and a snapshot literal makes a healthy refresh red the deterministic
suite. Every existing guarantee — rule 2 no invented values, byte-identical no-op, retirement
announced AND recorded, new ids appended with their live context, local tier and paid pin
untouched — MUST remain asserted.

#### Scenario: the suite is green on both the old and the refreshed catalogue

- **Given** a repository at the pre-refresh chain (five free ids) and one at the refreshed chain
  (three free ids, two retirements)
- **When** `test_agent_model_chain`, `test_agent_profile_provision` and `test_free_model_refresh`
  run against each tree
- **Then** all three are green on both trees, including the retirement, no-op and context-drift
  cases, without any test-file edit between them
- **Test:** tests/test_free_model_refresh.py::test_a_retired_free_model_drops_and_a_retired_primary_hands_over
- **Test:** tests/test_free_model_refresh.py::test_an_unchanged_live_set_writes_nothing
- **Test:** tests/test_free_model_refresh.py::test_a_context_drift_follows_the_live_read

#### Scenario: a snapshot fixture is refused by a catalogue-agnostic guard

- **Given** test modules that still spell a currently-shipped free id as a fixture literal
- **When** the new fixture guard runs on those modules
- **Then** it fails naming each stale literal and the file that carries it; on the fixed modules
  it passes for any free set read from the chain
- **Test:** tests/test_free_model_refresh.py::test_the_fixtures_follow_the_live_chain_not_a_snapshot
