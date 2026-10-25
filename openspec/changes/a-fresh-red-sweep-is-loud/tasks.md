# Tasks

- [x] 1. Write the proposal + `sweep-delivery-alarm` capability spec for issue #498 (the alarm half).
- [x] 2. `scripts/sweep_alarm.py`: a fresh non-`success` delivery is a verdict (`fresh: true`, reason names the conclusion).
- [x] 3. `scripts/sweep_alarm.py`: `render()` distinguishes a dropped cron from a sweep that ran and failed.
- [x] 4. `tests/test_sweep_alarm.py`: the misleading 4.8 h fixture replaced by a real fresh failure; fresh success still health; fresh cancelled loud; CLI exit 1 for fresh-red.
- [x] 5. Verified RED against `origin/master`'s `sweep_alarm.py` (3 failures, all `None`) and GREEN after (23 passed).
- [x] 6. `findings.md` written; the issue's comment half recorded as out of scope (protected §6j table).
- [x] 7. `OPENSPEC.md` regenerated; `make lint`, `make openspec-check`, `make architecture-check`, `make findings-check` green.
