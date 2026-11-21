# fleet-model-chain

## ADDED Requirements

### Requirement: The chain carries a credential-less local tier between the free steps and the paid pin

The chain MAY carry exactly one `role: "local_fallback"` entry (issue #1192). When present it MUST
sit AFTER every `primary`/`fallback` step and BEFORE the single `last_resort`; it MUST name its OWN
`provider` and `base_url` (never the chain's remote endpoint), the BARE model id its server answers
(no `provider/` prefix), and a measured `context_window`; and it MUST carry NO `key_env` and no
credential field — the local box is credential-less. The gate MUST refuse two local tiers, a local
tier out of position, a local tier inheriting or naming the remote endpoint, a local tier with a
`key_env`, and a local tier whose model id is not bare. Every existing refusal (one primary, ≥1 free
fallback, paid pin LAST equal to the Makefile pins, credential NAMES only) is unchanged.

#### Scenario: the shipped chain's local tier is well-formed and positioned

- **Given** `agents/model_chain.json` as shipped
- **When** the chain is read
- **Then** exactly one `local_fallback` sits after every free step and immediately before the
  `last_resort`, names its own provider/base_url different from the chain's, carries no `key_env`,
  and names a bare server model id
- **Test:** tests/test_agent_model_chain.py::test_every_free_step_comes_before_the_paid_last_resort

#### Scenario: every broken local-tier shape is refused in words

- **Given** a scratch tree whose chain carries one of the nine broken local shapes (two locals,
  local before the free fallbacks, local after the last resort, local with `key_env`, local naming
  the remote endpoint, local missing provider, local missing base_url, local with a provider/model
  id, local with an `api_key` value)
- **When** `scripts/agent_model_chain.py --check` runs
- **Then** each case exits 1 with a `[model-chain] FAIL` line stating the defect
- **Test:** tests/test_agent_model_chain.py::test_the_local_tier_is_guarded_like_every_other_tier

### Requirement: The rendered config carries the runtime fallback order

`render_text` MUST emit a `fallback_providers:` list walking every non-primary chain step in order
(free fallbacks, then the credential-less local tier, then the paid pin), each entry naming
`provider`/`model`/`base_url` and — for remote steps only — `key_env`; the local entry carries no
credential. The local alias block in `model_aliases:` MUST carry its own provider/base_url and NO
`key_env` line. This is the order Hermes' own `fallback_config.py` resolves at run time.

#### Scenario: the rendered lane config walks free -> local -> paid with a credential-less local step

- **Given** the shipped chain and a rendered lane config
- **When** the config's `fallback_providers:` and `local-strata` alias block are read
- **Then** the fallback models appear in chain order, the local entry names `provider: strata` and
  its own `base_url` with no `key_env`, every remote entry names `key_env: NOUS_API_KEY`, and the
  local alias block carries no `key_env`
- **Test:** tests/test_agent_model_chain.py::test_the_rendered_config_carries_the_runtime_fallback_order_and_a_credential_less_local_alias

### Requirement: A non-lane profile home is MERGED, never rewritten

`scripts/agent_profile_provision.py --profile <name>` MUST replace ONLY the `model:`,
`model_aliases:` and `fallback_providers:` top-level blocks of `<profiles-home>/<name>/config.yaml`
with the rendered chain's blocks; every other top-level block and the home's leading prose MUST
survive byte-for-byte, verified after the merge, and the prior file MUST be kept as
`config.yaml.bak-<UTC>` (rule 3b). The merge MUST be idempotent. `--profile default` names the Hermes
home's own `config.yaml` beside the profiles root. A fleet lane named via `--profile` is refused
(lanes are whole copies via `--lane`), a profile home that does not exist is refused (provisioning
never creates a profile), and the credential pre-flight is unchanged: the remote steps still demand
their `key_env` — the local tier never makes provisioning keyless.

#### Scenario: a non-lane merge keeps every other byte and repeats cleanly

- **Given** a scratch profile home whose config carries a stale strata-first `model:` block plus
  `custom_providers:`, `terminal:` and `auxiliary:` blocks and a leading comment
- **When** `--profile developer` runs twice
- **Then** the owned blocks equal the rendered chain's byte-for-byte, every other block and the
  leading comment survive unchanged, the prior config is kept as a backup, and the second run
  changes no byte
- **Test:** tests/test_agent_profile_provision.py::test_a_non_lane_profile_merges_only_the_owned_blocks_and_keeps_every_other_byte

#### Scenario: default names the Hermes home's own config; lanes and missing homes are refused

- **Given** a scratch profiles root with a prior `config.yaml` beside it
- **When** `--profile default`, then `--profile tll-tester`, then `--profile no-such-home` run
- **Then** default merges the home's own config (backup kept), the lane name is refused naming
  `LANE=`, the missing home is refused naming its path, and no credential value reaches any file
  or output
- **Test:** tests/test_agent_profile_provision.py::test_default_names_the_hermes_homes_own_config_and_a_lane_via_profile_is_refused

### Requirement: The PROFILE= seam is wired through the Makefile

`make agent-profile-provision` MUST accept `PROFILE=<name>[,<name>…]` (a comma list expanded to one
`--profile` per name through the Makefile's own `comma` variable) beside `LANE=`/`ALL=`/
`PROFILES_HOME=`, and the wiring test MUST refuse a Makefile that loses it.

#### Scenario: the wiring is asserted, and removing it is red

- **Given** this repository's Makefile and this test module
- **When** `test_the_target_is_wired_to_the_makefile_and_a_pipeline_job` runs
- **Then** `PROFILE ?=`, `comma := ,` and the per-name `--profile` expansion are present, the
  existing LANE/ALL/PROFILES_HOME wiring and the qa-validate caller are unchanged, and
  `wiring.wired(__file__)` is true
- **Test:** tests/test_agent_profile_provision.py::test_the_target_is_wired_to_the_makefile_and_a_pipeline_job
