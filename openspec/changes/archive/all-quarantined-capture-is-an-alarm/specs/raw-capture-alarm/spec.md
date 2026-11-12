# raw-capture-alarm

## ADDED Requirements

### Requirement: A capture with zero surviving rows is unusable, not a green no-op

`scripts/self_correct_raw.py` MUST exit non-zero, printing a distinct `CAPTURE UNUSABLE`
line, when it read at least one snapshot but the capture ended with ZERO model rows
surviving correction (whether every row was quarantined or every snapshot was captured
empty). A capture that kept even one row keeps its existing exit code, so one bad row beside
healthy ones still never discards the remainder (issue #381).

#### Scenario: every row of the capture is quarantined

- **Given** a temp data dir with one snapshot whose model rows all carry an un-derivable `hf`
  and none resolve to the store
- **When** the real `scripts/self_correct_raw.py` command runs against it
- **Then** it exits non-zero, prints a `CAPTURE UNUSABLE` line, still reports every row
  `QUARANTINED:`, and leaves no model in the snapshot
- **Test:** tests/test_raw_quarantine.py::test_a_capture_where_every_row_is_quarantined_is_unusable

#### Scenario: a partial quarantine still exits 0

- **Given** a snapshot carrying one un-derivable row beside a good one
- **When** the real command runs
- **Then** it exits 0, the good row survives, and the un-derivable row is reported
  `QUARANTINED:` only
- **Test:** tests/test_raw_quarantine.py::test_an_underivable_model_is_quarantined_and_the_rest_merges

#### Scenario: nothing-read remains distinct from nothing-survived

- **Given** a capture where no snapshot can be read at all
- **When** the real command runs
- **Then** it exits non-zero and prints `SELF-CORRECT INCOMPLETE`, not `CAPTURE UNUSABLE`
- **Test:** tests/test_raw_quarantine.py::test_a_capture_where_no_snapshot_can_be_read_is_the_unusable_state
