# fleet-model-chain

## ADDED Requirements

### Requirement: A verified no-op free-tier read is recorded additively

When a live Nous catalogue read finds the chain's free tier already current, the chain MUST carry a
`measured.verified` record of that read: its UTC `at`, the `endpoint` read, the catalogue's model
count, the number of `:free` models and the full list of `:free` ids. Every id in the record MUST be
one of the chain's `primary`/`fallback` steps, the recorded count MUST equal the number of those
steps, and the endpoint MUST equal the chain's `base_url`. The record MUST NOT carry a credential
value or a credential-shaped field (rule 3e). Existing `measured` keys (`at`, `how`, `issue`,
`previous_read`, `local`) and every chain step MUST remain byte-identical: the verification is
additive only (rule 3b).

#### Scenario: the shipped chain records the live read that verified its unchanged free tier

- **Given** `agents/model_chain.json` as shipped with five free steps and the live read of
  2026-11-21T20:14:30Z (415 models, five `:free` ids matching the shipped windows)
- **When** the chain is read by the gate and its test
- **Then** `measured.verified` names that timestamp, endpoint, 415 catalogue models, five free
  models and the five exact ids; the free steps, local tier and paid pin are unchanged
- **Test:** tests/test_agent_model_chain.py::test_the_chain_records_its_live_free_tier_verification

#### Scenario: a record that disagrees with the chain or names a credential is refused

- **Given** a scratch chain whose `measured.verified` names an id that is not a free step, omits one
  that is, carries a different endpoint, or adds a key/token/secret field
- **When** the verification guard is applied
- **Then** the check fails with the mismatch named, and no chain value was rewritten
- **Test:** tests/test_agent_model_chain.py::test_verification_record_refusals_are_red
