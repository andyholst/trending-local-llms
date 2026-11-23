# Tasks: local-endpoint-probe-1352

- [x] Add `scripts/local_endpoint_probe.py` — the capped live probe (`--probe`) and the offline `--check`, reading the `local_fallback` tier from the ONE chain
- [x] Record `measured.local.last_probe` + an additive `probe_history`; a DOWN result is recorded, not dropped
- [x] Add the `LOCAL_PROBE_TIMEOUT_SECONDS` / `LOCAL_PROBE_MAX_AGE_HOURS` / `LOCAL_PROBE_HISTORY_MAX` pins and the `_local-endpoint-probe`/`local-endpoint-probe` + `_local-endpoint-probe-check`/`local-endpoint-probe-check` targets
- [x] Bundle `local-endpoint-probe-check` into `make lint`; keep the live probe out of every merge gate
- [x] Add `tests/test_local_endpoint_probe.py` driving the REAL seam against a REAL local HTTP server (live / dead / slow / missing / drifted / stale / unreadable / dry-run / wiring)
- [x] Seed the shipped chain's `measured.local` record and prove the shipped tree passes the offline check
- [~] Add the `AGENTS.md` §8 guard row for `tests/test_local_endpoint_probe.py` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Update `ARCHITECTURE.md` §3 + §6 and regenerate §10
- [x] Regenerate `OPENSPEC.md` and run `make lint`, `make architecture-check`, `make openspec-check` and `make test`
- [x] Write `findings.md` with the owed-row declaration and push the branch for review
