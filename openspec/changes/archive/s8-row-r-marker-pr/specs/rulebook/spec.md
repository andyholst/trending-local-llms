## ADDED Requirements

### Requirement: The §8 row names the guard that locks the R marker's PR field

`AGENTS.md` §8's `tests/test_watch_monitor.py` row SHALL name issue #1284 and the
`test_r_marker_carries_its_pull_request` guard, so the `:<pr>` field on an `R:` marker has a
rulebook home.

#### Scenario: A reader can find what locks the PR field

- **Given** the §8 table
- **When** a reader looks for the `R:` marker's PR field
- **Then** the `tests/test_watch_monitor.py` row names #1284 and `test_r_marker_carries_its_pull_request`
- **Test:** tests/test_agents_rows.py::test_the_section_still_parses_as_a_table

#### Scenario: The row stays a well-formed table row

- **Given** the edited row
- **When** the §8 table is parsed
- **Then** it is one row with the same column count as the header
- **Test:** tests/test_agents_rows.py::test_the_section_still_parses_as_a_table
