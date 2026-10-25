# agents-rulebook

## ADDED Requirements

### Requirement: The §8 table documents the storage-offload guards

`AGENTS.md` §8 MUST carry a row for the guards issue #364 shipped, placed with the
`tests/test_data_gap_analysis.py` rows it belongs to: it MUST name
`tests/test_data_gap_analysis.py`, the two guards
(`test_storage_offload_backfill_traces_to_the_captured_source_text`,
`test_storage_offload_coverage_can_never_shrink`) and what they catch — an
invented `storage_offload`, and the closed gap silently reopening.

A guard that exists in the suite but is absent from §8 is undiscoverable from the
rulebook, which is the defect rule 6c exists to prevent.

#### Scenario: a reader finds the storage-offload guard in the rulebook

- **Given** the fetched tree with the #364 guards in `tests/test_data_gap_analysis.py`
- **When** §8 of `AGENTS.md` is read
- **Then** a row names `test_storage_offload_*`, the `storage_offload` dimension, the invented-value and reopening failures, and the measured `41/49` the filed issue recorded
- **Test:** `tests/test_agents_rows.py::test_the_owed_rows_are_present`

### Requirement: An owed §8 row cannot go missing again

The row MUST be pinned by a test, so deleting it turns the suite red instead of
quietly un-documenting the guard, and the module the row names MUST really define
the guards and run them from its `main()` (rule 6d — a guard no target executes is
a defect, not a spare part).

The pin MUST fail against the pre-change `AGENTS.md`.

#### Scenario: the row is deleted

- **Given** an `AGENTS.md` §8 without the `test_storage_offload_*` row (the pre-change file, `git show origin/master:AGENTS.md`)
- **When** `tests/test_agents_rows.py` runs
- **Then** it FAILS, naming the row it could not find
- **Test:** `tests/test_agents_rows.py::test_the_owed_rows_are_present`

#### Scenario: the row names a guard that is not wired

- **Given** the real `tests/test_data_gap_analysis.py`
- **When** the pin runs
- **Then** both guards exist in that module and its `main()` calls them, so `make test` really executes what the row claims
- **Test:** `tests/test_agents_rows.py::test_the_rows_name_modules_that_exist`
