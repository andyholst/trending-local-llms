# pipeline-failure-filer Specification

## Purpose
TBD - created by archiving change filer-skip-cancelled-push-runs. Update Purpose after archive.

## Requirements

### Requirement: A superseded cancelled push-to-master run files nothing

A `push`-to-`master` run whose conclusion is `cancelled` and whose jobs yielded no failing step,
no `make` target and no readable error block SHALL NOT become a tracked failure, an issue or a
ledger row. GitHub cancels the older validation when a newer push lands, so such a run never
concluded a delivery and carries no failure text to file (rule 6r). The skip SHALL be announced by
the sweep, in `--dry` as well as live, naming how many superseded runs were dropped.

#### Scenario: Nine cancelled push-to-master runs with unreadable logs

- **Given** nine in-window `event=push`/`headBranch=master`/`conclusion=cancelled` runs whose job
  logs cannot be read (`gh: HTTP 404`)
- **When** the master/schedule half of the filer sweeps its window
- **Then** no issue is filed for them and no ledger row names any of their run ids
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_is_not_filed

#### Scenario: The skip is previewed and counted

- **Given** the same nine superseded runs and a `--dry` sweep
- **When** the sweep previews its work
- **Then** it prints one announcement naming the number of superseded runs dropped and writes
  neither an issue nor a ledger
- **Test:** tests/test_pipeline_failure_issue.py::test_the_superseded_skip_is_announced_in_dry_output

### Requirement: The skip never swallows a real diagnosis

A cancelled run whose log DID yield a failing step, `make` target or error block SHALL still file
exactly as before (issue #1615), and a `cancelled` `schedule` run — a dropped delivery, which
`BAD_CONCLUSIONS` deliberately keeps — SHALL still be tracked even when its log is unreadable
(filed `UNDIAGNOSED`, loudly).

#### Scenario: A cancelled push run with a readable error block

- **Given** one `event=push`/`headBranch=master`/`conclusion=cancelled` run whose cancelled job's
  log carries a real error block
- **When** the sweep collects it
- **Then** exactly one issue is filed and its ledger row carries the diagnosis
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_with_a_readable_diagnosis_still_files

#### Scenario: A cancelled schedule run with an unreadable log

- **Given** one `event=schedule`/`conclusion=cancelled` run whose log cannot be read
- **When** the sweep collects it beside the nine superseded push runs
- **Then** the schedule run is filed `UNDIAGNOSED` while the nine push runs file nothing
- **Test:** tests/test_pipeline_failure_issue.py::test_a_cancelled_push_run_is_not_filed

### Requirement: Window-walk runs carry the workflow name the REST endpoint serves

The failure filer SHALL project a run's `workflowName` from the REST `actions/runs` `name` field. The REST endpoint has no `workflow_name` field, so a projected run SHALL never yield `workflowName = None` merely because it came from the paginated window walk. The projection SHALL live in the single `_RUN_ROW_FIELDS` mapping shared by the window walk (rule 6d).

#### Scenario: A real REST row names the workflow

- **Given** a REST `actions/runs` row carrying `name: "qa-validate"` and no `workflow_name` key
- **When** `_project_run` projects it to the camelCase run shape
- **Then** `workflowName` equals `qa-validate`, not `None`
- **Test:** tests/test_pipeline_failure_issue.py::test_window_rest_name_projects_workflow_name

#### Scenario: A filed issue and ledger row name the workflow

- **Given** a window-walk failure run whose REST row has only `name`
- **When** the filer files the issue and appends its ledger row
- **Then** the issue title and the ledger `workflow` field name the workflow, not `None`
- **Test:** tests/test_pipeline_failure_issue.py::test_window_filing_names_the_workflow_not_none

### Requirement: A dispatched run of a dispatch-only pipeline stays tracked

A concluded-bad `workflow_dispatch` run of a dispatch-only pipeline SHALL be recognised as tracked by `_is_tracked_failure` when its workflow name is present, so rule 6r files it instead of silently skipping it.

#### Scenario: Dispatch-only failure with a projected workflow name

- **Given** a `workflow_dispatch` run of a dispatch-only pipeline whose REST row carries its name in `name`
- **When** the filer projects the run and evaluates `_is_tracked_failure`
- **Then** the run is tracked and eligible to file
- **Test:** tests/test_pipeline_failure_issue.py::test_dispatch_only_run_tracked_with_projected_name
