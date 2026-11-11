# Tasks

- [x] 1. Write the proposal + `bot-alarms` capability spec for issue #488.
- [x] 2. `scripts/bot_health.py`: cron pipelines derived from the workflows (a `- cron:` line with an optional trailing comment), newest N `schedule` runs per pipeline, failure when all N are bad.
- [x] 3. Refusals: an empty pipeline list, `--limit 0`, and a `gh` that cannot answer are all non-zero — never a clean bill of health.
- [x] 4. `make bot-health` (`REPO=`, `LIMIT=`), host-side.
- [x] 5. `.github/workflows/bot-health.yml`: cron `23 */6 * * *` + dispatch, `guard` FIRST, `contents: read` + `actions: read`, calls the target.
- [x] 6. `tests/test_bot_health.py` (20 checks, stub `gh`): red/mixed/young/gh-down/limit-0, the derived pipeline list, and the workflow's shape.
- [x] 7. `tests/test_workflows.py`: `bot-health.yml` in `BOT_GUARDS` and `DISPATCH_ONLY_COVERAGE` (904 passed).
- [x] 8. `ARCHITECTURE.md` rows for the new target, script and pipeline; `make openspec-check`, `make architecture-check`, `make lint` green.
