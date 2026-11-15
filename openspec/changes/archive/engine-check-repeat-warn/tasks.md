# Tasks: engine-check-repeat-warn

- [x] `capture_date()` / `engine_first_seen()` / `decision_settled()` seams in `scripts/engine_registry.py` (first-seen from the oldest dated capture; no new state file) — verified by the new suite
- [x] `main()` window verdict: `--refresh-window-days` (7) + `--now`, NEW stays exit 0, REPEAT exits 1 naming the resolutions, declared refusals settle to OK — verified by the new suite
- [x] `tests/test_engine_registry.py` — five new tests green on the new code (261/261) and RED on the pre-change seam (repeat/new/declined/oldest-dated each assert the exit code the old always-green check did not have)
- [x] Shipped-store gate: `test_shipped_raw_has_no_stale_warn` green against real `data/raw` + `data/models.json`
- [x] `AGENTS.md` §6 refresh-workflow engine-check text + §8 guard row updated (rule 3c/6h)
- [x] `ARCHITECTURE.md` §5 `make engine-check` row + §6 `engine_registry.py` row updated
- [x] Local gates green (`make lint`, `make test`, `make engine-check`, secret-scan, `make openspec-check`) — suite 121 modules green; the 2 openspec-state modules re-ran green on the clean rebased tree (archive race, not a regression)
- [x] PR opened with the five-section body and `closes #972`; change archived at the PR head (PR #1070, `make openspec-record-pr ISSUE=972 PR=1070`)
