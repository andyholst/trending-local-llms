# Tasks: nvidia-before-registry-1864

- [x] Cut a worktree from freshly fetched `origin/master` (base `805a741f7a6cc61c5b8704d7894ed760a9f1348b`) on branch `fix/nvidia-before-registry-1864` after the signed claim and race guard
- [x] Add `is_nvidia_gpu()` in `scripts/update_trending.py` and apply the NVIDIA-before-registry guard in `measurement_backend()`, preserving Apple/Mac and CPU-only precedence
- [x] Add the RED-first real-file guard `tests/test_nvidia_before_registry.py`: 13 named rows CUDA, every explicit-NVIDIA row CUDA, TensorFold-on-Mac Metal, CPU-only CPU — RED on base 805a741f (PASSED 17 | FAILED 15), GREEN on head (PASSED 32 | FAILED 0)
- [x] Run `make render-readme` twice: rc=0 both times, byte-identical README (sha256 `3bbaa7952a6ac5b8de8860cb5d5b40e4c3990787b802d0fa9adf7a7529104d5d`), 1045 t/s DGX Spark figure moved from the Metal best cell to CUDA with no unrelated churn
- [x] Add this change dir (proposal + Given/When/Then spec + ticked tasks) and regenerate `OPENSPEC.md`
- [x] Run `make test`, `make lint`, `make openspec-check` and `make architecture-check` green
- [x] Open PR READY with `Closes #1864` in BOTH title and body; run `make pr-message-check PR=<n>` before the issue handover; record the PR with `make openspec-record-pr ISSUE=1864 PR=<n>`
- [~] Rule 6c `AGENTS.md` §8 row for the new guard — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); full row text declared on issue #1864
