## ADDED Requirements

### Requirement: Per-model freshness verdict

The rollup CLI SHALL accept `--model-id <id>` and print a read-only audit with newest
measurement date, days behind the newest stored date, historical and in-window row
counts, median parsed t/s, engine and architecture counts, and a VERDICT that
distinguishes a capture gap from a rank decision. An unknown id SHALL be reported
explicitly. It SHALL NOT write either store.

#### Scenario: Measured model with no in-window rows

- **WHEN** `--model-id qwen3.8-flash-next-125b` is run with a 7-day window
- **THEN** the audit reports its historical rows and newest measurement date
- **AND** the VERDICT names the capture gap and refs #1234

#### Scenario: Unknown id

- **WHEN** the id has no store row
- **THEN** the audit says MODEL NOT FOUND and gives no trend verdict
