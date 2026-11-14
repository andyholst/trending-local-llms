# Tasks

- [x] 1. The tracked change exists (this directory) before any edit.
- [x] 2. `refresh-bot.yml` gathers data WEEKLY — twice on Wednesday: `0 6 * * 3` + `43 17 * * 3`.
- [x] 3. `issue-bot.yml` sweeps weekly — twice on Wednesday: `19 * * * 3` + `49 * * * 3`.
- [x] 4. `issue-review-bot.yml`, `architecture-bot.yml`, `bot-health.yml`, `queued-alarm.yml`, `pr-health.yml`, `code-review-bot.yml` each run once, on Wednesday (`* * 3`), off the hour.
- [x] 5. The alarm scripts measure a WEEK: `freshness_alarm.DEFAULT_MAX_AGE_HOURS` 14 → 170; `sweep_alarm` default 3 → 168, `missed_slots()` counts Wednesday deliveries, and no hourly/daily prose survives.
- [x] 6. The rulebook and description move with them: `AGENTS.md` §6b / §6j / §6e / §8 and `ARCHITECTURE.md` §4 prose say weekly-Wednesday, and the GENERATED §10 inventory block is regenerated (`make architecture-refresh`), never hand-edited.
- [x] 7. The cadence is pinned by a test: `tests/test_workflows.py::test_every_pipeline_runs_weekly_on_wednesday` (every `on.schedule` cron ends `* * 3`; refresh-bot's two slots; all others one) plus the updated pins in `tests/test_workflows.py`, `tests/test_architecture_bot.py`, `tests/test_sweep_alarm.py`, `tests/test_freshness_alarm.py`.
- [x] 8. Verified: `make lint`, `make _validate`, `make _test`, `make architecture-check`, `make openspec-tasks-check`, `make openspec-index-check` green on the change tree.
- [x] 9. `findings.md` written (`make findings-check`); `OPENSPEC.md` regenerated (`make openspec-index`).
