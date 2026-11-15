# agents2-docstring-inventory-row-947

## ADDED Requirements

### Requirement: §2 rule 6h states the docstring-staleness trap

`AGENTS.md` §2 rule 6h MUST state, contiguously inside the §2 span, the owed-row
ledger needle `a docstring-only edit under scripts/ is enough to stale the
inventory block`, naming the measured defect (#947) and the
`tests/test_architecture_bot.py` staleness pin, so a change touching a script
docstring is contracted to ride `make architecture-refresh` in the same commit.

#### Scenario: the §2 span carries the contiguous ledger needle

- **Given** the shipped `AGENTS.md`
- **When** the §2 span ("## 2. Hard rules" up to "## 3.") is sliced
- **Then** it contains the contiguous needle `a docstring-only edit under
  scripts/ is enough to stale the inventory block` and the sentence names
  #947 and `tests/test_architecture_bot.py`
- **Test:** tests/test_agents_rows.py::test_the_docstring_staleness_row_is_written

#### Scenario: the owed-row ledger reports the row landed

- **Given** `make owed-rows-check` walks the ledger needles against the
  rulebook (`scripts/owed_rows_check.py`)
- **When** the §2 sentence lands on `master`
- **Then** issue #947's row reports LANDED with an `AGENTS.md:<line>` needle
  match inside its declared section — never OUTSTANDING again while the row
  exists
