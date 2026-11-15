# agents8-implement-stream-row-1062

## ADDED Requirements

### Requirement: §8 names the agent-leg test-image guard

`AGENTS.md` §8 carries a guard-table row for
`tests/test_implement_stream.py` — the pins that keep every `hermes` agent leg
running in the test-capable image — and the row holds the owed-row ledger
needle `test_implement_stream` contiguously inside the §8 span. A guard test
MUST pin the row so it cannot rot back to prose.

#### Scenario: the §8 span carries the contiguous ledger needle

- **Given** the shipped `AGENTS.md`
- **When** the §8 span ("## 8. Regression guards") is walked
- **Then** one needle-contiguous row names
  `tests/test_implement_stream.py::test_agent_legs_run_in_the_test_image`,
  names the issues that measured the failure (#833) and landed it (#1057), and
  declares the owed row it closes (#1062)
- **Test:** tests/test_agents_rows.py::test_the_implement_stream_row_is_written

#### Scenario: the owed-row ledger reports the row landed

- **Given** `make owed-rows-check` walks the ledger needles against the
  rulebook (`scripts/owed_rows_check.py`)
- **When** the §8 row lands on `master`
- **Then** issue #1062's row reports LANDED with an `AGENTS.md:<line>` needle
  match inside its declared section — never OUTSTANDING again while the row
  exists
