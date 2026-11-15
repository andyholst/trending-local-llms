## ADDED Requirements

### Requirement: The §8 row owed by the per-entry gap-filing dedup is written and pinned

`AGENTS.md` §8 MUST carry the row #996 owed (tracked as #1001), naming
`test_a_fluctuating_starved_leg_refiles_only_the_new_entry`, `test_a_gap_set_is_filed_once` and
`test_one_issue_per_changed_gap_set`, and `tests/test_agents_rows.py` MUST fail when that row is
removed or stops naming its guards and the issues that measured the failure.

#### Scenario: the landed guard has its rulebook row

- **Given** the §8 table of `AGENTS.md` after this change
- **When** `tests/test_agents_rows.py::test_the_per_entry_dedup_row_is_written` searches it
- **Then** one row names `test_a_fluctuating_starved_leg_refiles_only_the_new_entry`, both
  companion guards, and issues #996/#1001
- **Test:** tests/test_agents_rows.py::test_the_per_entry_dedup_row_is_written

#### Scenario: a removed row goes red

- **Given** the §8 row deleted from `AGENTS.md`
- **When** `tests/test_agents_rows.py` runs
- **Then** the pin fails naming the missing guard row (the gap cannot rot back to prose)
- **Test:** tests/test_agents_rows.py::test_the_per_entry_dedup_row_is_written

#### Scenario: the owed-row ledger reports the row LANDED

- **Given** issue #1001's registered owed-row marker (`section=8`,
  `needle=tests/test_data_gap_analysis.py --`) and the §8 row containing that needle verbatim
- **When** `make owed-rows-check` walks the queue against this tree
- **Then** the row reports `LANDED` with its `AGENTS.md:<line>` evidence and no OUTSTANDING
  problem for #1001
- **Test:** tests/test_owed_rows.py::test_a_landed_owed_row_is_reported_with_evidence
