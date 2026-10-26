# agents-guard-registry

## ADDED Requirements

### Requirement: The owed §8 rows are written and pinned

`AGENTS.md` §8 MUST carry one row for each guard this change's ledger lists, and
`tests/test_agents_rows.py` MUST fail when a row is removed or stops naming its guard and the issue
that measured the failure.

#### Scenario: every owed row is present

- **Given** the §8 table
- **When** the rows are read
- **Then** each of #543, #474, #362, #580/#583, #592, #522, #547/#548/#539/#578, #544, #563 and
  #363 has a row that names its guard and describes what it catches
- **Test:** tests/test_agents_rows.py::test_the_rows_this_session_owed_are_written

#### Scenario: the marker that was owed is registered

- **Given** `scripts/bot_markers.py`
- **When** the registry is read
- **Then** `issue-bot-already-fixed` is a registered `issue-bot` marker, `UNREGISTERED_OWED` is
  empty, and §6j names it
- **Test:** tests/test_agents_rows.py::test_the_rows_this_session_owed_are_written

#### Scenario: a removed row is loud

- **Given** the §8 table with one of those rows deleted
- **When** the guard runs
- **Then** it fails naming the issue and the phrase it expected
- **Test:** tests/test_agents_rows.py::test_the_rows_this_session_owed_are_written
