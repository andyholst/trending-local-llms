# Tasks

- [x] 1. The tracked change exists (this directory) before any chain/script/test edit
- [x] 2. `agents/model_chain.json`: `provider` `nous`; order `free-qwen4` (primary) →
      `free-longcat` → `strata-local` → `free-hy4` → `free-solar` → `free-step` →
      `nous-deepseek` (last_resort); the local step carries its own `provider`/`base_url`
- [x] 3. `scripts/agent_model_chain.py`: per-entry `provider`/`base_url`/`key_env`; the free-tier
      rule exempts a step on a different provider; a `nous` step with `base_url`/`key_env` is
      refused; the renderer omits empty values
- [x] 4. `scripts/agent_profile_provision.py`: the credential pre-flight runs only when the chain
      names a `key_env`
- [x] 5. `tests/test_agent_model_chain.py` + `tests/test_agent_profile_provision.py` updated in
      the same change, with new guards for the `nous`-step shape and the local step
- [x] 6. Gates green on the exact head: `make lint`, `make test`, `make openspec-check`,
      `make architecture-check` (with `make architecture-refresh`)
- [x] 7. Host act after the merge: `make agent-profile-provision ALL=1` and the default profile
      updated, reported on issue #1199
