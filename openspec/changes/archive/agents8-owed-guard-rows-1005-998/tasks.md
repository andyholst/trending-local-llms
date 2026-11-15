# Tasks: agents8-owed-guard-rows-1005-998

- [x] AGENTS.md §8 gains the row owed by #1002 (tracked #1005), carrying the contiguous needle `tests/test_data_gap_analysis.py::test_the_gap_issue_body_ends_with_a_newline`
- [x] AGENTS.md §8 gains the row owed by #993 (tracked #998), carrying the contiguous needle `tests/test_issue_triage.py::test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row`
- [x] `tests/test_agents_rows.py` gains `test_the_gap_body_newline_row_is_written` and `test_the_ledger_evidence_close_row_is_written`; the suite passes and each pin fails on a deleted row
- [x] `make owed-rows-check` reports both rows LANDED with `AGENTS.md:<line>` evidence
- [x] Gates green: `make lint`, `make openspec-check`, index current; PR carries paired `closes` bindings for #1005 and #998 and its own change archived at the head
