# Tasks: dgx-gb10-cuda-1866

- [x] Cut a worktree from freshly fetched `origin/master` (base `e711acd6e1d48b99150b6e0c8ac94706cdc2dc16`) on branch `fix/dgx-gb10-cuda-1866` after the signed claim and race guard
- [x] Enumerate every real-store row whose classification changes when `dgx`/`gb10` join `_CUDA_HW` (six), and record an evidence-backed decision for each in `findings/1866.md`
- [x] Append `dgx` and `gb10` to the ONE `_CUDA_HW` token set in `scripts/update_trending.py` (NVIDIA guard, AMD exclusion, CPU check and keyword fallback share the vocabulary)
- [x] Add the RED-first real-file guard `tests/test_dgx_gb10_cuda.py` over the REAL flattened store and its own engines registry, no stand-ins/monkeypatch: RED on base e711acd6 (PASSED 21 | FAILED 16), GREEN on head (PASSED 37 | FAILED 0)
- [x] Run `make render-readme` twice: rc=0 both, byte-identical README (sha256 `bf830cf5f091cbadfe8b75d569f953a599aac080d9a9449384cae4552a993250`), DGX figures moved out of Metal with no unrelated churn
- [x] Add this change dir (proposal + Given/When/Then spec + ticked tasks) and regenerate `OPENSPEC.md`
- [x] Run `make test`, `make lint`, `make openspec-check` and `make architecture-check` green
- [x] Open PR READY with `Closes #1866` in BOTH title and body; run `make pr-message-check PR=<n>` before the issue handover; record the PR with `make openspec-record-pr ISSUE=1866 PR=<n>`
- [~] Rule 6c `AGENTS.md` §8 row for the new guard — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); full row text declared on issue #1866
