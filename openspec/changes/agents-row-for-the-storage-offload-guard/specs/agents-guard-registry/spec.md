# agents-guard-registry

## ADDED Requirements

### Requirement: The §8 row a change owed is WRITTEN, naming the guards it describes

`AGENTS.md` §8 MUST carry a row for the `storage_offload` guards that closed the ranked
`storage_offload` gap (#364, PR #366). The row MUST name both guards by name
(`test_storage_offload_backfill_traces_to_the_captured_source_text` and
`test_storage_offload_coverage_can_never_shrink`), MUST name the module they live in
(`tests/test_data_gap_analysis.py`), and MUST state what they catch: a value no captured
`data/raw/*.json` text states (an invented value), a value on a model with no real
`…/status/<id>` post behind it, and the closed dimension silently reopening (a coverage floor).
The row MUST sit beside the existing `tests/test_data_gap_analysis.py` rows, and §8 MUST still
parse as a markdown table.

#### Scenario: the owed row is present and names its guards

- **Given** the `storage_offload` change (#364 / PR #366) whose §8 row could not be written
- **When** a reader opens `AGENTS.md` §8
- **Then** one row names `tests/test_data_gap_analysis.py`, both `test_storage_offload_*` guards,
  and the invented-value / coverage-floor failures they catch
- **Test:** tests/test_agents_rows.py::test_the_storage_offload_row_is_written

#### Scenario: the guards the row names really exist

- **Given** the row written for the `storage_offload` guards
- **When** the row's module is read
- **Then** each guard the row names is a function defined in it, so a renamed or deleted guard
  turns the pin RED instead of leaving a row that describes nothing
- **Test:** tests/test_agents_rows.py::test_the_rows_name_modules_that_exist

#### Scenario: the added row does not break the table

- **Given** §8 with the new row
- **When** the section is parsed row by row
- **Then** the header still names `Guard`, every row still carries at least a guard and a
  description, and no row has been swallowed by an unescaped pipe
- **Test:** tests/test_agents_rows.py::test_the_section_still_parses_as_a_table
