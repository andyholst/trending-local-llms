## ADDED Requirements

### Requirement: The candidate set covers the whole window

The filer SHALL take its main-pipeline candidates from a paginated window walk, not a fixed
`--limit 30` list, and SHALL report a partially-covered window loudly. The same helper SHALL serve
the PR-blockage scan. A window walk that hits its page cap SHALL NOT be read as a complete scan.

#### Scenario: A failure older than the thirty cap is still a candidate

- **Given** a page of 100 newer green runs and a second page holding one in-window concluded-bad push-to-master run
- **When** the main-pipeline scan runs
- **Then** the page-2 run is a candidate, an issue is filed for it, and its ledger row lands
- **Test:** tests/test_pipeline_failure_issue.py::test_the_main_pipeline_scan_walks_the_window_past_the_thirty_cap

#### Scenario: The PR-blockage scan shares the window walk

- **Given** an in-window shared `pull_request` failure older than 100 newer runs of its workflow, on two open PRs
- **When** `record_pr_blockages` runs
- **Then** the shape is grouped and filed once, and both call sites are source-checked to go through `window_runs`
- **Test:** tests/test_pipeline_failure_issue.py::test_the_pr_blockage_scan_uses_the_same_window_walk

### Requirement: Marker-carrying runs are reconciled directly

The filer SHALL fetch every unfiled marker-carrying run by id, so a filed failure is reconciled
into the ledger regardless of its rank in any run list. A fetched run that is not an in-window
tracked failure SHALL produce a named skip line and NO row.

#### Scenario: A marker run past the old cap reaches the ledger

- **Given** a tech-debt issue carrying `pipeline-run-failure: ... run=<R>` while 30 newer runs fill the old candidate window and `<R>` is absent from it
- **When** the sweep runs
- **Then** a ledger row for `<R>` exists carrying the marker issue's number and url, and the sweep names `<R>`
- **Test:** tests/test_pipeline_failure_issue.py::test_a_marker_run_past_the_old_cap_is_still_reconciled_into_the_ledger

#### Scenario: An out-of-scope marker run writes nothing

- **Given** marker runs answering `success`, older than the cutoff, or `event: pull_request`
- **When** the reconcile pass classifies them
- **Then** each prints a named skip line and NO ledger row is invented
- **Test:** tests/test_pipeline_failure_issue.py::test_a_marker_run_that_is_not_an_in_window_failure_writes_no_row

### Requirement: The marker scan has one implementation

`pipeline_failure_guard_check.marker_issue_states` SHALL delegate to the filer's marker seam, and
no second copy of the `gh issue list` scan SHALL exist in the tree.

#### Scenario: The guard reads the filer's map

- **Given** an issue carrying the registered `pipeline-run-failure` marker
- **When** the guard's `marker_issue_states` runs against the real seam
- **Then** it returns the gate's `{run_id: {number, state}}` shape, and the guard source carries no `gh issue list` call of its own
- **Test:** tests/test_pipeline_failure_issue.py::test_the_marker_scan_has_one_implementation
