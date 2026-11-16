# agents2-owed-row-1014

## ADDED Requirements

### Requirement: Hard rule 2 names its gap-filer dedup guard

Hard rule 2 of `AGENTS.md` ("Never fabricate data") states, inside the §2
span, the guard that keeps the data-gap filer's dedup marker a complete line:
`tests/test_data_gap_analysis.py` (`make test`). The row is the owed-row
ledger row declared by issue #1014
(`section=2 needle=tests/test_data_gap_analysis.py`); the guard test pins the
row so it cannot rot back to prose.

#### Scenario: the §2 span carries the contiguous ledger needle

- **Test:** tests/test_agents_rows.py::test_the_section2_row_names_the_gap_filer_guard
- **Given** the shipped `AGENTS.md`
- **When** the §2 span ("## 2. Hard rules" up to "## 3.") is sliced
- **Then** it contains the contiguous needle `tests/test_data_gap_analysis.py`
  and the guard sentence names the issue that measured the defect (#1002) and
  the PR that landed its guard (PR #1003)

#### Scenario: the owed-row ledger reports the row landed

- **Test:** tests/test_agents_rows.py::test_the_section2_row_names_the_gap_filer_guard
- **Given** `make owed-rows-check` walks the ledger needles against the
  rulebook (its own guard, `scripts/owed_rows_check.py`)
- **When** the §2 row lands on `master`
- **Then** issue #1014's row reports LANDED with an `AGENTS.md:<line>` needle
  match inside its declared section — never OUTSTANDING again while the row
  exists
