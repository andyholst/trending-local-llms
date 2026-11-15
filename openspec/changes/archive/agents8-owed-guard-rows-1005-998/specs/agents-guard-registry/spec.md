## ADDED Requirements

### Requirement: The §8 rows owed by the gap-body newline guard and the ledger-evidence close gate are written and pinned

`AGENTS.md` §8 MUST carry the two rows owed by #1002 (tracked as #1005) and #993 (tracked as
#998). Each row MUST contain its ledger needle verbatim and contiguous —
`tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline` and
`tests/test_issue_triage.py::test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row`
— and `tests/test_agents_rows.py` MUST fail when either row is removed or stops naming its
guard and the issues that measured it.

#### Scenario: both landed guards have their rulebook rows

- **Given** the §8 table of `AGENTS.md` after this change
- **When** `tests/test_agents_rows.py::test_the_gap_body_newline_row_is_written` and
  `tests/test_agents_rows.py::test_the_ledger_evidence_close_row_is_written` search it
- **Then** one row names the newline guard and issues #1002/#1005, the other names the
  ledger-evidence gate and issues #993/#998
- **Test:** tests/test_agents_rows.py::test_the_gap_body_newline_row_is_written
- **Test:** tests/test_agents_rows.py::test_the_ledger_evidence_close_row_is_written

#### Scenario: a removed row goes red

- **Given** either §8 row deleted from `AGENTS.md`
- **When** `tests/test_agents_rows.py` runs
- **Then** its pin fails naming the missing guard row (the owed row cannot rot back to prose)
- **Test:** tests/test_agents_rows.py::test_the_gap_body_newline_row_is_written
- **Test:** tests/test_agents_rows.py::test_the_ledger_evidence_close_row_is_written

#### Scenario: the owed-row ledger reports both rows LANDED

- **Given** the two issues' registered owed-row markers (`section=8`, the two needles) and
  the §8 rows containing those needles verbatim
- **When** `make owed-rows-check` walks the queue against this tree
- **Then** both rows report `LANDED` with their `AGENTS.md:<line>` evidence and no
  OUTSTANDING problem for #1005 or #998
- **Test:** tests/test_owed_rows.py::test_a_landed_owed_row_is_reported_with_evidence
