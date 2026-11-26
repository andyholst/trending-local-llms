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

### Requirement: The shipped ledger carries a real workflow name on every row

The append-only ledger SHALL carry a `workflowName` key on every row, named from the authoritative REST `actions/runs` `name` field of that row's run id. The backfill SHALL be additive only: no existing key or value may be removed, renamed or shrunk (rule 3b) — the legacy `workflow` spelling, including historical `None` strings, is preserved verbatim.

#### Scenario: Every shipped ledger row has a real workflow name

- **Given** `data/pipeline_failures.json` with 85 rows, 51 of which historically carry `workflow: "None"`
- **When** the additive backfill runs from each row's run id through REST `.name`
- **Then** every row carries a `workflowName` from the real name set and every pre-existing key/value is byte-identical
- **Test:** tests/test_pipeline_failure_issue.py::test_the_committed_ledger_carries_a_real_workflow_name_per_row

### Requirement: The workflow-name projection never regresses to the null REST field

The filer SHALL keep projecting `workflowName` from REST `name`; a regression to the always-null `workflow_name` would reintroduce `None` on every future row and re-break the board.

#### Scenario: The projection maps from name, not workflow_name

- **Given** the ONE `_RUN_ROW_FIELDS` mapping in `scripts/pipeline_failure_issue.py`
- **When** the guard reads that mapping
- **Then** `workflowName` maps from `name` and `workflow_name` appears in no projected value
- **Test:** tests/test_pipeline_failure_issue.py::test_the_committed_ledger_carries_a_real_workflow_name_per_row
