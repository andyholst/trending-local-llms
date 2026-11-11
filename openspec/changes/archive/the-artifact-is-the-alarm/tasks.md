# Tasks

- [x] 1. Write the proposal + `bot-alarms` capability spec for issue #452.
- [x] 2. `scripts/freshness_alarm.py`: the newest snapshot by the timestamp IN ITS NAME, an injected `--now`, `MAX_AGE_HOURS` (default 14), the newest scheduled refresh-bot run reported, and the remedy named.
- [x] 3. Refusals: no snapshot (or an unreadable one) exits 2 — a blind read is never health; a touched mtime never makes a stale tree fresh.
- [x] 4. `make freshness-alarm [REPO= MAX_AGE_HOURS=]`.
- [x] 5. `queued-alarm.yml`: the step runs AFTER the sweep alarm, in the same guarded job with the default token (no sixth pipeline).
- [x] 6. `tests/test_freshness_alarm.py` (14 checks, injected clock): fresh, stale + remedy, newest-wins, no-snapshot, mtime, and the workflow's placement.
- [x] 7. `ARCHITECTURE.md` rows for the target and the script, and the queued-alarm §4 section names the new step; `make openspec-check`, `make architecture-check`, `make lint` green.
