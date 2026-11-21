# Proposal: nous-provider-chain

Issue: #1203 — "fleet: the chain's custom + NOUS_API_KEY path cannot run inference — the provider must be nous"

## Why

Issue #1192 landed the credential-less local Strata tier but kept `provider: custom` +
`key_env: NOUS_API_KEY`. Measured on this host (2026-11-21) that path **cannot run a turn**:

- `curl -X POST https://inference-api.nousresearch.com/v1/chat/completions` with the profile's
  `NOUS_API_KEY` → `HTTP 401: Your API key is invalid, blocked or out of funds`.
- `hermes -p tll-planner -m free-longcat -z "…"` → the same 401.
- `GET /v1/models` with the SAME key → `200` (415 models): the key is model-list-only.
- The built-in **`nous`** provider (the Nous Portal session; the same endpoint) **does** run a
  turn, and adding `base_url`/`key_env` to a `nous` alias re-routes it to `custom` and 401s.

## What Changes

- `agents/model_chain.json`: `provider` `custom` → **`nous`**; the remote steps carry no
  `base_url`/`key_env`. The `local_fallback` tier (#1192) is unchanged.
- `scripts/agent_model_chain.py`: a remote step may carry its own `base_url`/`key_env`; a `nous`
  step carrying either is REFUSED (measured 401); a `custom` chain must still name `NOUS_BASE` and
  the alias `key_env`; the renderer omits empty values.
- `scripts/agent_profile_provision.py`: the credential pre-flight runs only when the chain names a
  `key_env` — a `nous` chain authenticates through the Portal session and names none.
- `tests/test_agent_model_chain.py` + `tests/test_agent_profile_provision.py`: updated in the same
  change (rule 6b), plus a new guard for the `nous`-step shape.

## Impact

- Every host fleet lane authenticates again (the Portal session) instead of 401ing.
- The CONTAINER legs are unchanged: they keep the Makefile's `HERMES_ALIAS` written with
  `provider: custom` + `NOUS_API_KEY` from the repository secret (a different credential from the
  host's, which is the one that 401s on inference).

## Not covered

- The chain ORDER: #1192 put `free-longcat` primary and `free-qwen4` third; the owner's 2026-11-21
  directive said qwen4-free primary. Kept #1192's order here — the owner can flip it on the issue.
- Actually running a local Strata model (no Strata engine is serving on this host right now).
- The host profiles themselves — a host act after the merge (`make agent-profile-provision`),
  reported on the issue.
