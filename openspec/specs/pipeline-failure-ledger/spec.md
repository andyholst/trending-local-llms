# pipeline-failure-ledger Specification

## Purpose
TBD - created by archiving change ci-keeper-ledger-45788860357. Update Purpose after archive.

## Requirements

### Requirement: A closed pipeline-failure issue with a landed fix carries a ledger row with its guard

When a pipeline-failure issue is CLOSED by a merged fix PR, `make pipeline-failure-guard-check`
MUST report the failure as landed rather than RED, by reading an append-only ledger row that names
that run, its merged `fix_pr`, and a guard test that `make test` collects. A CLOSED marker issue with
no ledger row at all is the recorded-red shape this change clears.

#### Scenario: the run 45788860357 row lands on the keeper branch

- **Given** issue #1763 (run 45788860357) is CLOSED by merged PR #1777 and the ledger holds no row for that run
- **When** the keeper branch appends the diagnosed row with `fix_pr` 1777 and guard `tests/test_openspec_archive_check.py`, then `make pipeline-failure-guard-check` runs on that head
- **Then** the gate exits 0 and no longer reports "issue #1763 (run 45788860357) is CLOSED but the ledger records nothing for that run"
- **Test:** tests/test_pipeline_failure_guard.py::test_closed_with_landed_fix_and_guard_is_green

#### Scenario: the missing-ledger-row shape is the locked failure class

- **Given** a CLOSED marker issue whose run id is absent from the ledger
- **When** `make pipeline-failure-guard-check` reads the ledger
- **Then** it REDs naming the run and the remedy to append the entry and its guard (append-only)
- **Test:** tests/test_pipeline_failure_guard.py::test_closed_marker_issue_the_ledger_never_recorded_is_red
