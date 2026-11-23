# Tasks: watch-marker-pr-identity-1355

- [x] Add the caller-owned `run_prs` map to `scripts/watch_monitor.py::marker_state` and reuse a recorded PR when `pull_requests` is cleared
- [x] Keep the marker shape unchanged: a push run keeps the shorter form, a PR run keeps `:<pr>`
- [x] Add `tests/test_watch_monitor.py::test_r_marker_keeps_its_pr_after_the_merge_clears_the_association` carrying the post-merge `pull_requests: []` shape
- [x] RED-prove the guard: base `scripts/watch_monitor.py` → 2 FAIL; restored → 60 passed / 0 FAILED
- [~] Extend the EXISTING `AGENTS.md` §8 row for `tests/test_watch_monitor.py` with the merge-surviving PR identity — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Update `ARCHITECTURE.md` §6's `scripts/watch_monitor.py` row and §3's `watch-monitor` row; regenerate §10
- [x] Regenerate `OPENSPEC.md` and run `make lint`, `make architecture-check`, `make openspec-check` and `make test`
- [x] Write `findings.md` with the owed-row declaration and push the branch for review
