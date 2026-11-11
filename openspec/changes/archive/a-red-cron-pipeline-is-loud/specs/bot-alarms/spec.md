# bot-alarms

## ADDED Requirements

### Requirement: A cron pipeline red on every scheduled run is loud

`make bot-health` MUST derive the repository's cron pipelines from the workflows, read each one's
newest N scheduled runs, and exit non-zero when all N failed, naming the newest run URL. It MUST NOT
report a clean result it did not measure (`gh` down, an empty pipeline list, `--limit 0`).

#### Scenario: a pipeline red on every run

- **Given** eight cron pipelines whose newest three scheduled runs all failed
- **When** the sweep runs
- **Then** it exits 1 and prints a run URL a human can open
- **Test:** tests/test_bot_health.py::test_a_pipeline_red_on_every_run_fails_the_sweep

#### Scenario: one green run inside the window

- **Given** a pipeline with two failures and one success in its window
- **When** the sweep runs
- **Then** that pipeline is reported `ok` (the others still fail the sweep)
- **Test:** tests/test_bot_health.py::test_one_green_run_is_enough_to_stay_quiet

#### Scenario: a young pipeline is not a failure

- **Given** a pipeline with fewer scheduled runs than the window
- **When** the sweep runs
- **Then** it is not treated as red
- **Test:** tests/test_bot_health.py::test_a_young_pipeline_is_not_a_failure

#### Scenario: gh cannot answer

- **Given** a `gh` that exits non-zero
- **When** the sweep runs
- **Then** it exits non-zero and names the failed read — never a clean bill of health
- **Test:** tests/test_bot_health.py::test_an_unanswerable_gh_is_loud_not_clean

#### Scenario: the pipeline list is derived

- **Given** this repository
- **When** the sweep lists its pipelines
- **Then** the cron workflows are named (including this alarm's own), and a non-cron pipeline is not
- **Test:** tests/test_bot_health.py::test_the_pipeline_list_is_derived_and_not_vacuous
