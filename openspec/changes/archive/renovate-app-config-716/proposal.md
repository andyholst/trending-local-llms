# Proposal: renovate-app-config-716

Issue: #716
PR: #1856

## Why

Issue #716 asks for weekly auto-bump PRs for pinned GitHub Action SHAs and Dockerfile base-image versions. Its original owner directive named a weekly-cron workflow, but the later #1029 rule (rule 6t) leaves `refresh-bot.yml` as the ONLY pipeline allowed an `on.schedule`, and `tests/test_workflows.py::test_only_the_refresh_pipeline_carries_a_schedule` fails any other cron. The reviewer confirmed the conflict (CONFLICT-CONFIRMED) and the planner ruled path (a): Renovate runs as the GitHub App, whose cadence is app-side.

## What Changes

- Add one root `renovate.json5`: an app-side weekly `schedule`, explicit `timezone`, `github-actions` and `dockerfile` managers, `separateMultipleMajor` and `dependencyDashboard`, with small PR limits.
- Add one guard in `tests/test_workflows.py` (`test_renovate_app_config_carries_the_weekly_cadence_without_a_workflow_cron`), called from `main()`, which fails when the config is missing/empty/loses its weekly cadence or either bump manager, and when any workflow gains a Renovate `on.schedule`.

## Impact

No workflow edit, no cron, no rulebook / SOUL / SKILL change, no data, README, schema or label change. The Renovate App must be installed by the owner before the config produces PRs; this change configures, it does not install (see `findings/716.md`).

## Not covered

- No repository `on.schedule` anywhere — the cadence lives in the App config.
- No relaxation of #1029, no rule-3c row, no second issue.
- No bump of tool images pinned outside Dockerfiles (Makefile pins); that is a separate scope.
