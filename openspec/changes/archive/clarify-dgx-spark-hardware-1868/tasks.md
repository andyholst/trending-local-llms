# Tasks: clarify-dgx-spark-hardware-1868

- [x] Read #1868's thread first; no competing lane claim; post signed `working on #1868` claim and re-read after the race-guard window (claim is newest)
- [x] Fetch `origin/master` (base `3c00bf44e969da4a07d87f9076b5bba6a81fe757`) and cut worktree branch `data/clarify-dgx-spark-hardware-1868` with `make worktree-new ... ISSUE=1868` (closure parser validated the `-1868` suffix)
- [x] Enumerate every real-store row carrying the target hardware string: exactly two, both under `qwen3.6-35b-a3b` (Ollama/87.2, Magnitude/188.9)
- [x] Add the RED-first real-file guard `tests/test_dgx_spark_hardware_clarification_1868.py` over the REAL store (no stand-ins/monkeypatch): RED on base `3c00bf44` (PASSED 15 | FAILED 6 — exactly the six missing-clarification checks), GREEN on head (PASSED 21 | FAILED 0)
- [x] Append the DGX-Spark clarification to exactly two `hardware` values in `data/measurements.json`, preserving the original text verbatim as a leading substring; no other stored value touched (`git diff --stat`: 2 insertions, 2 deletions)
- [x] Keep PR #1867's `tests/test_dgx_gb10_cuda.py` green: make its delta-row lookup tolerant of an additive hardware suffix; all classification assertions and the six-row enumeration unchanged (PASSED 37 | FAILED 0 on head)
- [x] Regenerate `README.md` with `make render-readme` twice: two renders byte-identical, churn confined to the two clarified cells
- [x] Run `make validate-data`: QA PASSED
- [x] Add this change dir (proposal + Given/When/Then spec + ticked tasks) and regenerate `OPENSPEC.md`
- [x] Run `make test`, `make lint`, `make openspec-check` — all rc=0
- [x] Open PR READY with `Closes #1868` in BOTH title and body; run `make pr-message-check PR=<n>` before the issue handover; record/archive the change with `make openspec-record-pr ISSUE=1868 PR=<n>`
- [~] Rule 6c `AGENTS.md` §8 row for the new guard — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); full row text declared on issue #1868
