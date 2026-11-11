# architecture-role-boundary

## ADDED Requirements

### Requirement: §6 role text carries a plain boundary statement

`ARCHITECTURE.md` §6 MUST state, in the lead-in before the role table, that the
Role column is human review text rather than a machine-verified claim: the guard
proves only that a row exists whose FIRST cell names the script, never that the
role text beside it still describes the code. Keeping a role true is a
reviewer's job.

#### Scenario: the lead-in names the boundary next to the rows

- **Given** the real `ARCHITECTURE.md`
- **When** a reader opens §6 between the heading and the `| Script | Role |` table
- **Then** the text plainly says the Role column is review text, not verified,
  and that the guard reads only the row's first cell
- **Test:** tests/test_architecture.py::test_section6_role_text_is_reviewed_not_verified

### Requirement: the top boundary and the §6 lead-in do not drift

The "What the guard proves — and what it does not" (§2 of the document intro)
MUST remain consistent with the §6 lead-in about the role column, and the module
docstring of `scripts/architecture_check.py` MUST state the same boundary, so
the document's promise and the guard's own words agree.

#### Scenario: the docstring and the document both call the role first-cell-prose

- **Given** the real `ARCHITECTURE.md` and `scripts/architecture_check.py`
- **When** the §6 lead-in, the top boundary and the `described_scripts()`
  docstring are read
- **Then** each names the role column as presence-only (first cell), never as
  machine-verified prose
- **Test:** tests/test_architecture.py::test_section6_role_text_is_reviewed_not_verified

### Requirement: removing the boundary statement turns the suite red

The guard for this must FAIL when the boundary language is weakened, so the
false "the check verifies role prose" implication cannot return silently.

#### Scenario: the plain statement is deleted

- **Given** a world where the §6 lead-in no longer says the role column is
  review text
- **When** `test_section6_role_text_is_reviewed_not_verified` runs
- **Then** it FAILS (the boundary is an asserted promise, not a comment)
- **Test:** tests/test_architecture.py::test_section6_role_text_is_reviewed_not_verified
