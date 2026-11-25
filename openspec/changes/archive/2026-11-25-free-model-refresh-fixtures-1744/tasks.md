# Tasks: free-model-refresh-fixtures-1744

- [x] Add `tests/fleet_chain_fixtures.py` with the one derivation seam (free steps, primary, alias order, fallback order, default needle)
- [x] Refactor `tests/test_free_model_refresh.py` to derive SHIPPED_FREE/SHIPPED_PRIMARY and retire/drift cases from the shipped chain
- [x] Refactor `tests/test_agent_model_chain.py` to derive order, fallback models and the hand-edit needle from the shipped chain
- [x] Refactor `tests/test_agent_profile_provision.py` to derive the primary needle from the shipped chain
- [x] Add the synthetic-chain guard that is RED on the frozen shape and GREEN on the fix
- [x] Prove all three modules green on the base chain and on the CI-red keeper head `3b76356492`
- [x] Run `make lint`, the targeted modules and the OpenSpec checks on the branch head
- [x] Write `findings/1744.md` and record the RED-on-keeper / GREEN-on-fix evidence for the delivery comment
