# Tasks — live-free-tier-verification-1226 (issue #1226)

- [x] Re-run the live Nous catalogue read with the credential passed by NAME and record the exact ids, windows and count (evidence: 2026-11-21T20:14:30Z, HTTP 200, 415 models, 5 `:free`)
- [x] Add `measured.verified` additively to `agents/model_chain.json`, preserving every existing key/value
- [x] Add the guard tests to `tests/test_agent_model_chain.py` and wire them into `main()`
- [x] Prove the guard is RED on the pre-change chain (`git show HEAD:agents/model_chain.json`)
- [x] `python3 tests/test_agent_model_chain.py` (standalone runner) green
- [x] `make agent-profile-model-render && make agent-model-chain-check` green (7 lane configs byte-unchanged)
- [x] Verify all 30 host `config.yaml` files (default + 29 profiles) still match the repo chain byte-for-byte
- [x] `make lint` and `make openspec-check` green; `findings.md` written
- [x] PR opened with five-section body and one `Closes #1226`; no merge, no CI dispatch
