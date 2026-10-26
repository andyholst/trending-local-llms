# agents-guard-registry

## ADDED Requirements

### Requirement: The storage_offload guards are discoverable from §8

`AGENTS.md` §8 MUST carry one row naming both `storage_offload` guards, the module they live in, what
each catches, and the change that added them; `tests/test_agents_rows.py` MUST fail when that row is
removed or when it loses any of those facts.

#### Scenario: the row is present and complete

- **Given** the §8 table in `AGENTS.md`
- **When** the rows are read
- **Then** one row names `test_storage_offload_backfill_traces_to_the_captured_source_text` and
  `test_storage_offload_coverage_can_never_shrink`, names `tests/test_data_gap_analysis.py`, states
  the invented-value and coverage-floor failures, cites `#364`/`#366`, and sits below the
  `engine_min_version` rows
- **Test:** tests/test_agents_rows.py::test_the_storage_offload_row_is_written

#### Scenario: the row cannot vanish quietly

- **Given** the same table with that row deleted
- **When** the guard runs
- **Then** it fails naming the missing guard
- **Test:** tests/test_agents_rows.py::test_the_storage_offload_row_is_written
