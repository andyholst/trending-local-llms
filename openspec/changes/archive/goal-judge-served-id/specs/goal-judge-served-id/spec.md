# goal-judge-served-id

## ADDED Requirements

### Requirement: The rendered lane config pins goal_judge to the chain's local model

Every `agents/tll-*/config.yaml` rendered from `agents/model_chain.json` SHALL set `auxiliary.goal_judge` to the chain's `local_fallback` provider, model, and base_url, and SHALL set `fallback_chain` to every other chain step: every `:free` Nous model, including the free primary, then the paid last resort. The local tier is the judge's own model and is not repeated. A `nous` hop SHALL carry only `provider` and `model`. `model.default` SHALL stay the free primary.

#### Scenario: the shipped render names the served local id and the Nous hops

- **Given** the shipped chain whose local tier is the model Strata serves
- **When** `make agent-profile-model-render` writes a lane config
- **Then** `auxiliary.goal_judge.model` equals that local model, `fallback_chain` lists every other chain step in chain order (every `:free` model included) with no `key_env`, and `model.default` is still the free primary
- **Test:** tests/test_agent_model_chain.py::test_the_rendered_goal_judge_pins_the_served_local_model
