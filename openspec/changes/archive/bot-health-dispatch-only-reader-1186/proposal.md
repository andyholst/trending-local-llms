# Proposal: bot-health-dispatch-only-reader-1186

**Issue:** [#1186](https://github.com/andyholst/trending-local-llms/issues/1186)
PR: #1490

## Why

`bot-health` derived its subject pipelines from a `- cron:` line only. After the owner cadence
directive of issue #1029, `refresh-bot.yml` is the repository's ONLY scheduled pipeline, so the
alarm measured one pipeline while its OWN pipeline (`bot-health.yml`) — and every other
dispatch-only bot — was red on all of its last ten recorded runs with nothing reading it. A red
alarm that removes its own alarm is the exact silence issue #488 created this pipeline to prevent.

## What Changes

- `scripts/bot_health.py` selects its watched pipelines BY ROLE: the cron set is kept, and a
  workflow whose only trigger is `workflow_dispatch` joins it. A cron pipeline is read with
  `--event schedule`; a dispatch-only pipeline with `--event workflow_dispatch`, its only delivery.
  `cron_pipelines()` and `scheduled_runs()` stay as additive, unchanged helpers.
- `bot-health.yml` joins `MAIN_PIPELINES` and `DISPATCH_ONLY_PIPELINES` in
  `scripts/pipeline_failure_issue.py`, so a concluded-bad dispatched run becomes a tracked
  marker-deduplicated `tech-debt` issue through `make pipeline-failure-issue` (rule 6r).
- RED-first guards in `tests/test_bot_health.py` (plus the wiring pin in `tests/test_workflows.py`)
  fail on the pre-change seam, with the younger-than-N and unreadable-`gh` verdicts preserved.
- `ARCHITECTURE.md` target/script/workflow rows describe the role-based selection.

## Impact

No data format, store contract, credential, image or workflow trigger changes. `bot-health` remains
owner-dispatch-only (no cron is re-added) and read-only (no issue writes). More workflows are now
read by the dispatch-only alarm; those with no dispatch runs report "no dispatched run yet" and stay
quiet, so a longer pipeline list is not a louder alarm.

## Not covered

- No AGENTS.md edit lands in this headless leg: the §6b `bot-health.yml` bullet and the §8 guard row
  are declared as owed rows in `findings.md` for human rule-3c sign-off.
- No CI dispatch, merge, master push, collaborator grant or new cron job.
- The flaky local strata endpoint (#1194) and the acquisition data gaps (#1126) are separate work.
