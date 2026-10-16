# data-gap-baseline

## ADDED Requirements

### Requirement: The baseline can be re-recorded without filing an issue

`make data-gap-baseline` MUST run `scripts/data_gap_analysis.py --write-baseline`,
so the "record the current gap signature as the baseline" path is reachable (rule
6d) instead of dead code. The target MUST be **host-side** — it writes
`data/gap_baseline.json` as the caller, never as root through the container mount —
and it MUST NOT be part of the refresh pipeline: run automatically it would set the
baseline to the current gap set on every refresh and silently stop the analysis
filing anything.

WHEN a baseline write is lost (a rebase, a refresh PR closed before it merged),
THEN a human can re-record it with `make data-gap-baseline`, and the file it writes
is the one the next run compares against.

#### Scenario: the flag is reachable from a make target

- **Given** the Makefile
- **When** the `data-gap-baseline` target is read
- **Then** it runs `python3 scripts/data_gap_analysis.py --write-baseline`, it is host-side (no `$(TEST_RUN)`), and no dead `_data-gap-baseline` wrapper is left behind
- **Test:** `tests/test_data_gap_analysis.py::test_analysis_is_wired_to_make_and_the_refresh_pipeline`

### Requirement: The written baseline IS the signature `changed()` reads

`--write-baseline` MUST record the current gap signature and file NOTHING. The file
it writes MUST equal `analyse(store)`'s signature exactly — that is the contract the
next run's `changed()` compares against — and a run against the freshly written
baseline MUST then see no change, so re-recording a lost baseline is stable and
idempotent.

WHEN `--write-baseline` runs,
THEN the baseline file is written, its signature equals `analyse(store)`'s, a
subsequent `--check` run exits 0, and no issue is filed.

#### Scenario: the file equals the live signature and the next run is a no-op

- **Given** a store and an absent baseline
- **When** `--write-baseline` runs (with no `gh` on PATH, so a filing would have failed)
- **Then** it exits 0, the written signature equals `analyse(store)`'s, and a `--check` run against it exits 0
- **Test:** `tests/test_data_gap_analysis.py::test_write_baseline_records_the_signature_without_filing`
