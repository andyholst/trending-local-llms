# Tasks: heartbeat-1282

- [x] Add opt-in `--heartbeat-seconds` and the deterministic `H:<bucket>` marker to `scripts/watch_monitor.py`
- [x] Forward the flag through `make watch-monitor` and accept `H:` in `CHECK=1`
- [x] Add RED-first guards for quiet tick, heartbeat boundary, failure coexistence and rulebook duty
- [~] Extend AGENTS.md rule 6w with H + the continue-working duty and §8 with the extended row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Update ARCHITECTURE.md target/script rows and regenerate `OPENSPEC.md`
- [x] Run focused test, `make lint`, `make architecture-check` and `make test`
- [x] Write `findings.md` and push the work onto PR #1267 for review
