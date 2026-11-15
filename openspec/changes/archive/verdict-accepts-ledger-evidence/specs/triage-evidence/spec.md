# triage-evidence

## ADDED Requirements

### Requirement: A close citing a merged pipeline-failure ledger row is checkable

A `close` verdict whose `EVIDENCE:` names `data/pipeline_failures.json` and a run id
MUST be accepted as checkable when the ledger resolves against the fetched base and the
row for that run id names a merged `fix_pr` and a `guard` test `make test` collects —
decided solely through `pipeline_failure_guard_check.read_ledger` and
`guard_test_exists` (rule 6d, no second ledger reader), and a visible non-ledger
evidence shape still passes as before.

#### Scenario: a ledger-backed close for an already-fixed failure proceeds

- **Given** a `close` verdict whose `EVIDENCE:` cites `data/pipeline_failures.json`
  with a run id whose ledger row names `fix_pr: 806` and `guard: tests/test_sweep_alarm.py`
- **When** the verdict is parsed and applied against that tree
- **Then** the verdict is `close`, the issue is closed and labelled `agent:closed`,
  and the evidence is posted with the reason
- **Test:** tests/test_issue_triage.py::test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row

#### Scenario: a ledger row with no merged fix is not checkable

- **Given** a `close` verdict whose `EVIDENCE:` cites `data/pipeline_failures.json`
  with a run id whose ledger row names no `fix_pr` (the fix is still in flight)
- **When** the verdict is parsed
- **Then** it is REFUSED (exit 2) and the issue is not touched, so a fix-in-flight
  failure cannot be closed away before its guard lands
- **Test:** tests/test_issue_triage.py::test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row

#### Scenario: a prose-only close is still refused

- **Given** a `close` verdict whose `EVIDENCE:` is only prose
- **When** the verdict is parsed
- **Then** it is REFUSED (exit 2) with no comment, no close, no label
- **Test:** tests/test_issue_triage.py::test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row
