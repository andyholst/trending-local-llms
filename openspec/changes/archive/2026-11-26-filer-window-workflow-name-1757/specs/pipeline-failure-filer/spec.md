# pipeline-failure-filer

## ADDED Requirements

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
