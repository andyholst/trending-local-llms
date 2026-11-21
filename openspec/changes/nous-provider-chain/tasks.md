# Tasks

- [x] 1. The tracked change exists (this directory) before any chain/script/test edit
- [x] 2. `agents/model_chain.json`: `provider` `nous`; the remote steps carry no `base_url`/`key_env`
- [x] 3. `scripts/agent_model_chain.py`: a remote step may carry its own `base_url`/`key_env`; a
      `nous` step carrying either is refused; the renderer omits empty values
- [x] 4. `scripts/agent_profile_provision.py`: the credential pre-flight runs only when the chain
      names a `key_env`
- [x] 5. `tests/test_agent_model_chain.py` + `tests/test_agent_profile_provision.py` updated in
      the same change, with a new guard for the `nous`-step shape
- [x] 6. Gates green on the exact head: `make lint`, `make test`, `make openspec-check`,
      `make architecture-check` (with `make architecture-refresh`)
- [x] 7. Host act after the merge: provision every `tll-*` profile home + the default profile from
      the rendered chain, verify each with a real turn, report on issue #1203
