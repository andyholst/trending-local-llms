# change-lifecycle Specification

## Purpose
TBD - created by archiving change openspec-record-pr-idempotent. Update Purpose after archive.

## Requirements

### Requirement: Recording a change's PR is idempotent

`make openspec-record-pr ISSUE=<n> PR=<m>` MUST exit **0** when re-run for an
issue whose change is already archived (the recording already happened),
naming the change as already recorded and editing nothing. It MUST still exit
**2** — loudly — when NO change, active or archived, references that issue.

#### Scenario: a re-run on an already-archived change is a no-op

- **Given** a fixture tree where `openspec/changes/my-change` references `Issue: #518`
- **When** `scripts/openspec_record_pr.py --issue 518 --pr 523` runs once (archives it), then runs again with the same arguments
- **Then** the second run exits 0, creates no active change, leaves the archived proposal unchanged, and prints that `my-change` is already recorded
- **Test:** `tests/test_openspec_record_pr.py::test_rerun_on_an_already_archived_change_is_a_noop`

#### Scenario: a genuinely unmatched issue still refuses

- **Given** a fixture tree where the only change references `Issue: #7`
- **When** `scripts/openspec_record_pr.py --issue 518 --pr 523` runs
- **Then** it exits 2 and names the unmatched issue
- **Test:** `tests/test_openspec_record_pr.py::test_record_refuses_when_no_change_names_the_issue`

### Requirement: The archiving lifecycle's promises are kept

The module docstring and the `AlreadyThere` exception it describes MUST be real:
a re-run never raises `NoSuchChange` for the already-archived state it documents
as a no-op.

#### Scenario: the documented AlreadyThere case is implemented

- **Given** `scripts/openspec_record_pr.py` on its own source
- **When** `tests/test_openspec_record_pr.py` runs
- **Then** every one of its assertions passes, including the no-op re-run case
- **Test:** `tests/test_openspec_record_pr.py`
