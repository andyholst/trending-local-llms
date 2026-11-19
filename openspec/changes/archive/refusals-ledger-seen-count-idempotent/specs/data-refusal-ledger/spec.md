## ADDED Requirements

### Requirement: A refusal finding is recorded once, and a repeat grows its counter

`record_ingest_refusals` SHALL key a refusal on
`(stage, model, engine, reason, source_post)`. A finding the ledger does not hold
SHALL append exactly one record carrying `seen_count: 1`. A finding the ledger
already holds SHALL NOT be appended again: its `seen_count` SHALL be raised by one
and `last_seen_utc` stamped, while its original `utc` (first sighting) and every
other recorded field SHALL stay byte-identical (rule 3b: a key may only be ADDED and
a counter may only GROW). The call SHALL announce the collapse in the log.

#### Scenario: A repeat of a recorded finding appends no copy

- **Given** a ledger that already holds a refusal finding written by a real ingest
  round over a real raw fixture
- **When** `record_ingest_refusals` is called again with the same
  (stage, model, engine, reason, source_post)
- **Then** the ledger holds the same number of records, each with `seen_count`
  raised to 2 and a `last_seen_utc`, with its `utc` and finding fields unchanged,
  and the log names the repeat
- **Test:** tests/test_ingest_refusal_ledger.py::test_a_repeat_of_a_finding_grows_seen_count_instead_of_appending

#### Scenario: A distinct finding still appends exactly one record

- **Given** a ledger written by a real ingest round
- **When** `record_ingest_refusals` records a finding whose reason and model the
  ledger does not hold, then records that same finding a second time
- **Then** the ledger gained exactly one record, it starts at `seen_count: 1`, the
  second arrival grew it to 2 without appending, and no two records in the ledger
  share a finding key
- **Test:** tests/test_ingest_refusal_ledger.py::test_a_distinct_finding_still_appends_exactly_one_record

### Requirement: Re-validating an unchanged tree changes only the counters

Running the ingest/validation pass a second time over an unchanged raw snapshot SHALL
leave every finding field of every ledger record byte-identical and SHALL append no
record; only `seen_count` / `last_seen_utc` may differ (`make validate` twice leaves
`data/refusals.json` byte-identical apart from those counters).

#### Scenario: A second validation pass over the same raw round

- **Given** a store and a raw round ingested once, producing a ledger of N records
- **When** the same raw round is ingested a second time over the resulting store
- **Then** the ledger still holds N records, every non-counter field of every record
  is byte-identical to the first pass, and every record carries `seen_count >= 1`
- **Test:** tests/test_ingest_refusal_ledger.py::test_a_second_validation_pass_changes_only_the_counters

### Requirement: The gap report's refusal total counts observations, never copies

`make data-gaps` SHALL carry `seen_count` into `refused_at_ingest` and SHALL print
the refusal total as the SUM of `seen_count` over the ledger (at least 1 per record),
so collapsing repeats into counters can never shrink a total an earlier report
printed (rule 3b).

#### Scenario: Growing the counters grows the printed total

- **Given** a real ledger produced by a real ingest round, rendered by the real
  `data_gap_analysis.render` with `seen_count` set high enough that the bounded
  render prints its total line
- **When** the same ledger is rendered with every `seen_count` raised by one
- **Then** the printed total equals the sum of `seen_count` in each render, the
  second total is larger than the first, and the ledger file on disk is unchanged
- **Test:** tests/test_ingest_refusal_ledger.py::test_the_reported_total_counts_observations_never_copies
