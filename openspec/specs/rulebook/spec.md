# rulebook Specification

## Purpose
TBD - created by archiving change land-the-owed-rulebook-rows. Update Purpose after archive.

## Requirements

### Requirement: The rulebook states the authorship rule, not just that a guard exists

`AGENTS.md` §2 MUST carry a rule naming the two allowed identities, the automation identities that
must not be refused, the fact that the guard reads the identity AND the message, and the loud
failure on an unreadable range.

#### Scenario: a reader asks who may commit

- **Given** `AGENTS.md` §2
- **When** a reader looks for the authorship rule
- **Then** rule `3f` names `Andy Holst`, `Asimov Agent`, `github-actions[bot]`, `GitHub <noreply@github.com>`, and `make check-commit-authorship`
- **Test:** tests/test_rule_numbers.py::main

### Requirement: The owed guard rows exist beside the guards they describe

Every guard that an owed-row issue named MUST have its §8 row, and the rows MUST carry the
measured failure rather than a generic phrase.

#### Scenario: the four owed rows

- **Given** `AGENTS.md` §8
- **When** the rows are read
- **Then** `engine_min_version`, the search legs' engine rule, the fix loop's time bound, and the derived guard registry each have a row, and the `tests/test_workflows.py` row names the agent identity instead of "no git identity"
- **Test:** tests/test_architecture.py::main

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
