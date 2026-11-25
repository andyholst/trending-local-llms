# Tasks: stale-claim-check-summary-1657

- [x] RED-first: add the pinned-phrase assertion to `tests/test_stale_claim_sweep.py::test_the_offline_contract_needs_no_network` and observe it FAIL on `ae574e3c` (PASSED 5 | FAILED 1)
- [x] Update the `--check` summary's live-run clause to `(x2 when the claim carries a run id, unless its evidence is still LIVE, #1265 §3B)` — output prose only
- [x] Prove GREEN on this head: the targeted test passes and `tests/test_stale_claim_sweep.py` reports PASSED 94 | FAILED 0
- [x] Confirm no behavioural change: AUTHORITY_LIMITS, the pinned pairs, the floors, the S: vocabulary and the exit codes are byte-identical outside the printed string
- [x] Regenerate `OPENSPEC.md`, bind the change to `Issue: #1657`, and run the deterministic OpenSpec checks green before opening the PR
