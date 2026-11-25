# Tasks: fleet-local-tier-fixtures-1750

- [x] Extend `tests/fleet_chain_fixtures.py` with one derivation of the local-tier needles (bare model, alias, provider, endpoint, paid alias) from a chain dict
- [x] Refactor `tests/test_agent_model_chain.py` to derive every local-tier needle in the rendered-config guard from the shipped chain
- [x] Refactor `tests/test_agent_profile_provision.py` to derive the local-tier survival needle from the shipped chain
- [x] Add the synthetic-local-tier guard that is RED on the frozen shape and GREEN on the fix, and wire it into `main()`
- [x] Prove the new guard RED on the pre-change (frozen) seam and GREEN on the fixed tree
- [x] Run the targeted modules, `make lint` and the OpenSpec gates on the branch head
- [x] Write `findings/1750.md`, regenerate `OPENSPEC.md` and prove the OpenSpec gates green
