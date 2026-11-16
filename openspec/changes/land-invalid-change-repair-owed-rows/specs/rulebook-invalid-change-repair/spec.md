# rulebook-invalid-change-repair — spec delta

## ADDED Requirements

### Requirement: The rulebook names the invalid-active-change repairer and its guard

`AGENTS.md` §2 (rule 6q) SHALL name `invalid-change-repair` as a qa-validate keeper of the
`openspec-check` gate — the repair for an ACTIVE change that shipped incomplete — and §8 SHALL
carry a guard row for `tests/test_openspec_invalid_change_repair.py`, and the landed rows SHALL
state the seam's real contract (three-state verdict, archive-only keeper, no fabricated spec or
task text). The rows are the ledger's, landed verbatim; a pin test locks them in the rulebook.

#### Scenario: §6q names the third repairer shape

- **Given** a reader of rule 6q asking which keeper repairs an INVALID active change
- **When** the rulebook text is read
- **Then** the paragraph names the incomplete-change shape, the `invalid-change-repair` job, its
  `DRIFT=none|index-drift|invalid-change` verdict, and the registry naming all three repairers
- **Test:** tests/test_agents_rows.py::test_the_invalid_change_repair_rows_are_written

#### Scenario: §8 carries the landed guard row and the modules it names exist

- **Given** a reader of the §8 guard table asking what catches a regression in the repair seam
- **When** the table row for `tests/test_openspec_invalid_change_repair.py` is read
- **Then** the row names the seam script and both Makefile targets, states the outranking and
  no-fabrication halves, and both named modules exist in the tree
- **Test:** tests/test_agents_rows.py::test_the_invalid_change_repair_rows_are_written

#### Scenario: the owed-row ledger reports the rows landed

- **Given** the two `owed-row` markers #1087 declares (`section=2 needle=invalid-change-repair`,
  `section=8 needle=tests/test_openspec_invalid_change_repair.py`)
- **When** `make owed-rows-check` walks the open queue against this tree's `AGENTS.md`
- **Then** both rows report `LANDED` with their `AGENTS.md:<line>` proof and `problems=0`
- **Test:** tests/test_owed_rows.py::test_a_landed_owed_row_is_reported_with_evidence
