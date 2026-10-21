# Tasks

- [x] 1. The measured gap is recorded on #497 before any code
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `scripts/sweep_alarm.py` — pure `stale()`/`missed_slots()`, render, exit 0/1/2
- [x] 4. `make sweep-alarm REPO=<owner/name> [MAX_AGE_HOURS=3]` — the only entry point
- [x] 5. `queued-alarm.yml` calls it (a step of its own, after the checkout)
- [x] 6. A second schedule slot on `issue-bot.yml`, off the `:19` it already used
- [x] 7. Tests: the measured fixture, no-delivery, red-last-delivery, three exit codes, the wiring
- [x] 8. `ARCHITECTURE.md` row + the §10 inventory regenerated
- [x] 9. `make test`, `make lint`, `make architecture-check`, `make openspec-check`, `make secret-scan` green; `OPENSPEC.md` regenerated
- [x] 10. `findings.md` written; the protected-file rows noted on #494
