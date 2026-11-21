# fleet-model-chain

## ADDED Requirements

### Requirement: The fleet chain runs on the Nous provider with a local-engine fallback

The fleet model chain MUST authenticate through the built-in `nous` provider (the Nous Portal
session), carry the free primary first and the free fallbacks in list order, allow a step to
declare its OWN `provider`/`base_url` so a LOCAL engine (Strata) rides in the same chain, and
MUST NOT put `base_url`/`key_env` on a `nous` step — measured, that re-routes the alias to
`custom` and answers HTTP 401.

#### Scenario: a `nous` step carrying `base_url`/`key_env` is refused

- **Given** a chain whose primary is a `nous` step
- **When** that step also carries `base_url` or `key_env`
- **Then** `make agent-model-chain-check` exits non-zero naming the measured 401, and the step is
  never rendered into a lane config
- **Test:** tests/test_agent_model_chain.py::test_a_nous_step_carrying_base_url_or_key_env_is_refused

#### Scenario: the local Strata step is exempt from the free-tier rule but must name its endpoint

- **Given** a `fallback` step on a DIFFERENT provider (the local Strata engine) whose model is not
  a `:free` Nous model
- **When** the chain is checked
- **Then** the step passes while it carries its own `provider`/`base_url`, and is REFUSED when
  either is stripped (it would then be a non-free fallback on the chain provider)
- **Test:** tests/test_agent_model_chain.py::test_a_local_step_is_exempt_from_the_free_rule_but_needs_its_endpoint

#### Scenario: a `nous` chain provisions with no credential pre-flight

- **Given** the shipped chain, which names no `key_env` (the Portal session authenticates it)
- **When** `make agent-profile-provision ALL=1` runs with NO credential in the environment
- **Then** every lane config lands byte-identical to the chain and the seam is green; a chain
  that DOES name a `key_env` still refuses (exit 2) when that variable is absent
- **Test:** tests/test_agent_profile_provision.py::test_the_nous_chain_provisions_with_no_credential_at_all
