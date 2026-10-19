# data-gap-baseline-age

## ADDED Requirements

### Requirement: The analysis reports which baseline it compared against

`make data-gaps` (and the issue the filer opens) MUST state the baseline's recorded
`as_of` and how many days before this analysis it was written, and the run log MUST
carry the same line.

#### Scenario: a baseline exists and is old

- **Given** `data/gap_baseline.json` recorded 40 days before the store's `generated_utc`
- **When** the analysis runs
- **Then** the report and the log name its `as_of` and the 40-day age
- **Test:** tests/test_data_gap_baseline_age.py::test_age_is_measured_from_the_baseline_as_of

#### Scenario: no baseline at all

- **Given** a baseline path that does not exist
- **When** the analysis runs
- **Then** no baseline line is reported and nothing crashes
- **Test:** tests/test_data_gap_baseline_age.py::test_age_is_measured_from_the_baseline_as_of

### Requirement: A stale baseline is loud, with its fix

When the baseline's age reaches `STALE_DAYS` the run MUST say so in the log and in the
report's findings, naming `make data-gap-baseline` as the repair — because an unchanged
gap set files nothing and would otherwise look like "nothing to file".

#### Scenario: the baseline is older than the stale threshold

- **Given** the real store and a baseline stamp older than 30 days
- **When** `scripts/data_gap_analysis.py --baseline <path>` runs
- **Then** it exits 0, the log carries `baseline is STALE` and the re-record command, and the report carries the same
- **Test:** tests/test_data_gap_baseline_age.py::test_the_run_log_shouts_when_the_baseline_is_stale

#### Scenario: a re-recorded baseline is not stale

- **Given** a baseline written from the current analysis
- **When** the analysis runs
- **Then** it still reports the baseline's stamp but never calls it stale
- **Test:** tests/test_data_gap_baseline_age.py::test_a_fresh_baseline_is_not_called_stale
