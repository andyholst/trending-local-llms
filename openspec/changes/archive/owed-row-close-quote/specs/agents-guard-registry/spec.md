# agents-guard-registry

## ADDED Requirements

### Requirement: Closing an owed-row issue quotes the ledger on the thread

`make issue-verdict`'s `close` comment MUST carry the issue's owed-row states —
each declared row quoted as LANDED with its `AGENTS.md:<line>` proof, or
OUTSTANDING — built by `owed_rows_check.owed_row_close_note`, which shares the
ONE landing decision (`row_states`) the report walks (rule 6d). A thread or
rulebook that cannot be read, a malformed marker, or a marker naming a section
that does not exist MUST refuse the close (exit 2) with nothing written. An
issue with no owed rows MUST close exactly as before.

#### Scenario: a landed row is quoted with its rulebook line

- **Given** a close verdict on an issue whose thread declares an owed row that has landed in §8
- **When** `make issue-verdict` applies the verdict
- **Then** the issue closes and the close comment quotes the row as LANDED with its rulebook line number and text
- **Test:** tests/test_issue_triage.py::test_close_quotes_the_landed_owed_row_with_its_agents_md_line

#### Scenario: an outstanding row is named and the close still proceeds

- **Given** a close verdict on an issue whose owed row has NOT landed
- **When** the verdict is applied
- **Then** the issue closes and the comment names the row OUTSTANDING with its needle
- **Test:** tests/test_issue_triage.py::test_close_records_an_outstanding_owed_row_and_still_closes

#### Scenario: a broken ledger read refuses the close

- **Given** a close verdict on an issue whose owed row names a section the rulebook does not have, or carries a malformed marker
- **When** the verdict is applied
- **Then** the verdict exits 2 naming the refusal, and no comment, close or label is written
- **Test:** tests/test_issue_triage.py::test_close_refuses_when_a_declared_section_does_not_exist
- **Test:** tests/test_issue_triage.py::test_close_refuses_a_malformed_owed_row_marker

#### Scenario: the note and the report land from one implementation

- **Given** the same planted thread and rulebook seen by the ledger report and by the close note
- **When** both readers run
- **Then** they agree on the landed line number and the outstanding needle, and the close note raises on the states the report would gate on
- **Test:** tests/test_owed_rows.py::test_the_close_path_and_the_report_land_from_one_implementation

#### Scenario: a plain close is untouched

- **Given** a close verdict on an issue with no owed-row marker
- **When** the verdict is applied
- **Then** the reason and evidence close comment is written unchanged, with no owed-rows section
- **Test:** tests/test_issue_triage.py::test_an_issue_without_an_owed_row_closes_without_a_ledger_section
