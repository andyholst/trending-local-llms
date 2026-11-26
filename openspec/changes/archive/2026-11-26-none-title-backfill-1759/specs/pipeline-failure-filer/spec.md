# pipeline-failure-filer

## ADDED Requirements

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
