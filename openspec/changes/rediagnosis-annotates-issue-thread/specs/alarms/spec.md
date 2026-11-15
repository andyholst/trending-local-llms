# alarms

## ADDED Requirements

### Requirement: A raised UNDIAGNOSED row posts ONE marker-deduplicated comment on its cited issue

`make pipeline-failure-issue`'s re-diagnosis pass MUST, when it raises a ledger row (adds
`rediagnosed_utc` + `error_excerpt` + `rediagnosis_note` for a row whose log became readable),
post ONE comment on the issue the row cites (`entry["issue_url"]` / `entry["issue_number"]`),
carrying the `pipeline-rediagnose` marker (shape defined in `scripts/bot_markers.py`) and quoting
the landed scrubbed `error_excerpt` and the grown `targets`. Before posting it MUST read the
issue's comments and skip when a `pipeline-rediagnose` marker for the same run id already exists —
one comment per raised row, never per sweep. The comment MUST be written with the default
`github.token`. A row with no cited issue is raised without a comment.

#### Scenario: a raise lands a single marker-deduplicated comment on the cited issue

- **Given** a ledger seeded with an UNDIAGNOSED row for run 100 whose `issue_url` cites issue 824,
  a stub `gh` serving readable logs, and a thread for issue 824 with NO `pipeline-rediagnose`
  comment for run 100
- **When** the sweep runs
- **Then** the row gains `rediagnosed_utc` and one comment is posted on issue 824 carrying the
  `pipeline-rediagnose` marker and quoting the scrubbed `error_excerpt` + `targets` — and the
  planted secret is masked
- **Test:** tests/test_pipeline_failure_issue.py::test_a_raise_annotates_the_cited_issue_once

#### Scenario: an issue already carrying the marker for the run is not commented twice

- **Given** the same UNDIAGNOSED row and a stub `gh` whose issue 824 thread ALREADY carries a
  `pipeline-rediagnose` comment for run 100
- **When** the sweep runs
- **Then** the row is still raised, and NO second comment is posted on issue 824
- **Test:** tests/test_pipeline_failure_issue.py::test_a_raise_does_not_double_annotate

#### Scenario: a raised row with no cited issue is raised without a comment

- **Given** an UNDIAGNOSED row whose `issue_url`/`issue_number` are None
- **When** the sweep raises it
- **Then** the row gains `rediagnosed_utc` and no comment is attempted
- **Test:** tests/test_pipeline_failure_issue.py::test_a_raise_with_no_issue_cites_no_thread
