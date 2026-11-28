# Tasks: renovate-app-config-716

- [x] 1. Add root `renovate.json5` with a weekly app-side `schedule`, explicit `timezone`, `github-actions` + `dockerfile` managers, `separateMultipleMajor` and `dependencyDashboard`
- [x] 2. Add `test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron` to `tests/test_workflows.py` and call it from `main()`
- [x] 3. RED-prove both failure shapes on the base tree (missing config: 7 FAIL, rc=1; planted Renovate workflow with `on.schedule`: 1 FAIL, rc=1) and restore GREEN (19 pass, 0 fail)
- [x] 4. Add this change bound to `Issue: #716`, write `findings/716.md`, and regenerate `OPENSPEC.md`
