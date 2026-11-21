# fleet-model-chain

## ADDED Requirements

### Requirement: A `nous` chain step carries only the provider

A fleet chain step on the built-in `nous` provider MUST NOT carry `base_url` or `key_env`: the
Nous provider supplies both (the Portal session authenticates it), and a measured alias that adds
them is re-routed to the `custom` provider and answers HTTP 401 on inference. A chain that names a
`key_env` is still credential-checked by the provisioning seam before a byte is written.

#### Scenario: a `nous` step carrying `base_url`/`key_env` is refused

- **Given** a chain whose primary is a `nous` step
- **When** that step also carries `base_url` or `key_env`
- **Then** `make agent-model-chain-check` exits non-zero naming the measured 401, and the step is
  never rendered into a lane config
- **Test:** tests/test_agent_model_chain.py::test_a_nous_step_carrying_base_url_or_key_env_is_refused

#### Scenario: a `nous` chain provisions with no credential pre-flight

- **Given** the shipped chain, which names no `key_env` (the Portal session authenticates it)
- **When** `make agent-profile-provision ALL=1` runs with NO credential in the environment
- **Then** every lane config lands byte-identical to the chain and the seam is green; a chain that
  DOES name a `key_env` still refuses (exit 2) when that variable is absent
- **Test:** tests/test_agent_profile_provision.py::test_the_nous_chain_provisions_with_no_credential_at_all
