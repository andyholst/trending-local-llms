# data-gap-analysis Specification

## Purpose
TBD - created by archiving change starved-leg-gap-files. Update Purpose after archive.

## Requirements

### Requirement: A whole starved leg files a gap; a single empty snapshot does not

For every backend seen in the raw search directory, the analysis MUST take that
backend's newest run (its 8-digit date stamp) and, when EVERY snapshot of that run
captured zero models, add `starved_leg:<backend>` to the issue-triggering signature
(the entry names the backend only, never the date) and report a loud finding naming
the snapshot count and run date. A backend whose newest run captured at least one
model MUST stay out of the signature, with its empty snapshots reported only as
informational.

#### Scenario: every snapshot of a leg's newest run captured nothing

- **Given** a raw directory whose `cpu` snapshots all carry `models: []` while `nvidia`'s newest snapshot carries a model
- **When** the store is analysed
- **Then** the signature carries `starved_leg:cpu` and not `starved_leg:nvidia`, and a `STARVED LEG cpu` finding names the snapshot count and the run date
- **Test:** tests/test_data_gap_analysis.py::test_a_whole_starved_leg_changes_the_signature

#### Scenario: one empty query inside a capturing leg stays informational

- **Given** a raw directory whose `nvidia` newest run holds one empty snapshot and one snapshot with a model, and a `metal` run that captured a model
- **When** the store is analysed
- **Then** no `starved_leg:` entry enters the signature and the empty snapshot is reported only in the informational line
- **Test:** tests/test_data_gap_analysis.py::test_a_single_empty_snapshot_stays_informational
