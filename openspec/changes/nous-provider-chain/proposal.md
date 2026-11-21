# Proposal: nous-provider-chain

Issue: #1199 — "fleet: run the lanes on the Nous provider — qwen4-free primary, longcat fallback, a local Strata step, deepseek last"

## Why

Measured on this host (2026-11-21): the fleet's rendered chain (`provider: custom` + `base_url`
nous + `key_env: NOUS_API_KEY`) is DEAD — `hermes -p tll-planner -m free-longcat -z "…"` answers
`HTTP 401: Your API key is invalid, blocked or out of funds`. The built-in **`nous`** provider
(the Nous Portal session; the same `https://inference-api.nousresearch.com/v1` endpoint) works: a
scratch profile with `model: {provider: nous, default: meituan/longcat-2.5:free}` answered a real
turn, and an alias `free-qwen4: {model: qwen/qwen4-max:free, provider: nous}` answered a real
turn. Adding `base_url`/`key_env` to a `nous` alias re-routes it to `custom` and 401s. The owner
also asked for qwen4-free in the primary slot, longcat as a fallback, a LOCAL Strata step, and the
remaining free models after them.

## What Changes

- `agents/model_chain.json`: `provider` `custom` → **`nous`**; the chain order becomes
  `free-qwen4` (primary) → `free-longcat` → `strata-local` → `free-hy4` → `free-solar` →
  `free-step` → `nous-deepseek` (last_resort); a new per-entry `provider`/`base_url` override
  carries the local Strata step (`qwen3.8-flash-next-q2_0` @ `http://127.0.0.1:8080/v1`).
- `scripts/agent_model_chain.py`: an entry may override `provider`/`base_url`/`key_env`; the
  free-tier rule exempts a step on a DIFFERENT provider (a local engine); a `nous` step carrying
  `base_url`/`key_env` is REFUSED (measured 401); the renderer omits empty `base_url`/`key_env`.
- `scripts/agent_profile_provision.py`: the credential pre-flight runs only when the chain names a
  `key_env` — a `nous` chain authenticates through the Portal session and names none.
- `tests/test_agent_model_chain.py` + `tests/test_agent_profile_provision.py`: updated in the same
  change (rule 6b), plus new guards for the `nous`-step shape and the local step.

## Impact

- Every host fleet lane authenticates again (the `nous` Portal session), with qwen4-free first.
- A lane can fall back to a local Strata-served model when the Nous endpoint is unreachable.
- The CONTAINER legs are unchanged: they keep the Makefile's `HERMES_ALIAS` written with
  `provider: custom` + `NOUS_API_KEY` from the repository secret (a different credential from the
  host's, which is the one that 401s).

## Not covered

- Actually running a local Strata model (no Strata engine is installed on this host); the step is
  wired and gated, and works when the engine is.
- The container legs' credential (out of scope; the repository secret is not this host's key).
- Updating the host profiles themselves — that is a host act the issue's owner runs after the
  merge (`make agent-profile-provision ALL=1`), recorded in the issue thread.
