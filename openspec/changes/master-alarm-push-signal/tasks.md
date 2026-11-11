# Tasks

- [x] 1. `scripts/master_alarm.py` — alarm reads the newest push-to-master qa-validate run; keeper/alarm registry
- [x] 2. `make master-alarm` internal `_master-alarm` + public wrapper (REPO/LIMIT)
- [x] 3. `queued-alarm.yml` alarm job gains the step (after the guard, through the Makefile)
- [x] 4. `tests/test_master_alarm.py` — red fixture goes red, green/pending/absent pass, registry covers every validate gate, workflow wiring, Makefile variables
- [x] 5. `AGENTS.md` rule 6q + §8 guard row
- [x] 6. `ARCHITECTURE.md` §3 target row, §4 queued-alarm step, §6 scripts row
- [x] 7. `make architecture-refresh` + `make architecture-check` green
- [x] 8. `make lint` green; `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 9. `make test` proven through CI (TEST image is CI's half)
