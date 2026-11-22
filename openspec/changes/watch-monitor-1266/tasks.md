# Tasks: watch-monitor-1266

- [x] Write `scripts/watch_monitor.py` with deterministic C/R/M markers and a CI-safe check mode
- [x] Add `make watch-monitor` and wire a `make watch-monitor CHECK=1` step into `qa-validate`
- [x] Add `tests/test_watch_monitor.py`; prove it RED on the base tree
- [x] Add AGENTS.md rule 6w + §8 row and ARCHITECTURE.md target/script rows
- [x] Regenerate `OPENSPEC.md`; run focused test, `make lint`, `make architecture-check`, `make test`
- [ ] Write `findings.md`, re-read the #1266 thread for a newer claim, and open a non-draft PR with exactly one closing keyword bound to #1266; record/archive the change on that branch
