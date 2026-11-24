## ADDED Requirements

### Requirement: Watch pipelines by role, not by cron alone

The alarm SHALL derive its watched pipelines from the workflow tree by role: every workflow with a
`- cron:` trigger AND every workflow whose only trigger is `workflow_dispatch`. A workflow with a
push or pull-request trigger SHALL NOT be watched by role alone, because a change exercises it
directly. The pre-existing cron-only helpers SHALL remain available and unchanged.

#### Scenario: A dispatch-only pipeline is watched

- **Given** a workflow whose only trigger is `workflow_dispatch`
- **When** the alarm lists its pipelines
- **Then** that workflow is listed, and a pull-request-only workflow is not
- **Test:** tests/test_bot_health.py::test_dispatch_only_pipelines_are_watched_by_role

### Requirement: Read each pipeline's own delivery event

A cron pipeline SHALL be read with `--event schedule`; a dispatch-only pipeline SHALL be read with
`--event workflow_dispatch`. A window shorter than N runs is not a failure, and an all-bad window
fails the sweep and names a run URL a human can open.

#### Scenario: All dispatch runs failed

- **Given** a dispatch-only pipeline whose newest N `workflow_dispatch` runs all failed
- **When** the alarm runs
- **Then** it exits 1 and names the newest dispatch run URL
- **Test:** tests/test_bot_health.py::test_a_dispatch_only_pipeline_red_on_every_dispatch_run_fails_the_sweep

### Requirement: A red dispatch of bot-health reaches the filer

`bot-health.yml` SHALL be a MAIN pipeline declared dispatch-only, so a concluded-bad dispatched run
is selected by `main_pipeline_failures` and filed through `make pipeline-failure-issue` (rule 6r).

#### Scenario: The failure filer watches bot-health

- **Given** a concluded-bad `workflow_dispatch` run of `bot-health.yml` inside the window
- **When** `main_pipeline_failures` selects runs
- **Then** that run is included, and the pipeline is named in both filer contracts
- **Test:** tests/test_bot_health.py::test_the_failure_filer_watches_the_bot_health_pipeline
