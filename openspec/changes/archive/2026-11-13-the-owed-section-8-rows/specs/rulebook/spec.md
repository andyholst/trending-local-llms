# rulebook

## ADDED Requirements

### Requirement: A guard registered in the suite is described in §8

The rows three changes owed MUST be present in `AGENTS.md` §8, naming the module and the failures
it catches.

#### Scenario: the owed rows

- **Given** AGENTS.md
- **When** the guard reads §8
- **Then** it names `tests/test_ci_wiring.py`, `tests/test_code_review.py` and
  `test_scratch_notes_stay_out_of_the_tree`, with the measured failure beside each
- **Test:** tests/test_agents_rows.py::test_the_owed_rows_are_present

#### Scenario: the rows are honest

- **Given** the modules and guards the rows name
- **When** the guard checks them
- **Then** each module exists and the named guard really lives in it
- **Test:** tests/test_agents_rows.py::test_the_rows_name_modules_that_exist

#### Scenario: the table is still a table

- **Given** the §8 section
- **When** the guard parses it
- **Then** it has a header row and every row carries a guard and a description
- **Test:** tests/test_agents_rows.py::test_the_section_still_parses_as_a_table
