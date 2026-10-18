# data-gap-backfill

## ADDED Requirements

### Requirement: A stated storage offload is stored, not left in prose

A gap dimension the contracts declare OPTIONAL — `storage_offload` here — MUST be
backfilled into the model-level structured field from the source post's own words
whenever the post states a storage-offload requirement, additively: no existing
key is removed or renamed and no existing value is shrunk. A model whose captured
text states nothing for the dimension MUST be left unset, so the gap stays
reported instead of being closed with an invented value.

WHEN a source post states that a run streams experts or weights from storage,
THEN the model carries that statement as a structured `storage_offload`.

#### Scenario: a stated storage offload becomes a structured value

- **Given** a model whose captured source text states the offload (e.g. `--moe-stream SSD-streamed experts` / `192GB engram on Gen4 7GB/s NVMe (MoE experts streamed from SSD to CPU)`) and which has no `storage_offload`
- **When** the store is backfilled
- **Then** the model carries `storage_offload` naming that offload, and no other key of the model is changed
- **Test:** `tests/test_data_gap_analysis.py::test_storage_offload_coverage_can_never_shrink`

#### Scenario: a model whose post states nothing is left unset

- **Given** a model whose captured text names only VRAM / RAM / GPU-layer offload or a machine's own SSD, with no experts or weights streamed from storage
- **When** the store is backfilled
- **Then** the model still has no `storage_offload` — the gap stays reported rather than closed with an invented value
- **Test:** `tests/test_data_gap_analysis.py::test_storage_offload_backfill_traces_to_the_captured_source_text`

### Requirement: Every structured value traces to the captured source text

A model-level `storage_offload` MUST be evidenced by the model's own captured
source text in `data/raw/*.json` — the snapshot of a real `…/status/<id>` post.
The value MUST name a storage medium that appears in that text, and every
size/capacity token of it MUST appear as well; a value that no captured post
supports is a fabrication and MUST fail the suite.

WHEN a structured dimension value is written into the store,
THEN the suite proves the post behind it says the same thing.

#### Scenario: the value is present in the captured text of a real post

- **Given** the real store and the raw search snapshots
- **When** the traceability guard runs
- **Then** every model carrying `storage_offload` names a storage medium its captured text names, has all of the value's size tokens present in that text, and has a real post URL on at least one of its measurements
- **Test:** `tests/test_data_gap_analysis.py::test_storage_offload_backfill_traces_to_the_captured_source_text`

#### Scenario: an invented value fails the guard

- **Given** a store whose model carries a `storage_offload` no captured snapshot mentions (e.g. `8TB tape library, experts streamed`)
- **When** the traceability guard runs
- **Then** it fails, naming the model
- **Test:** `tests/test_data_gap_analysis.py::test_storage_offload_backfill_traces_to_the_captured_source_text`

### Requirement: The closed gap cannot silently reopen

The dimension's coverage MUST be asserted against a floor, so a change that drops
the backfilled value (or a regeneration that loses it) turns the suite red.

WHEN the store is regenerated without the backfill,
THEN the coverage guard fails.

#### Scenario: coverage floor holds on the real store

- **Given** the real store after this change
- **When** the coverage guard runs
- **Then** at least 9 models carry a structured `storage_offload` and the analysis reports fewer models missing it than the 41 the filed issue recorded
- **Test:** `tests/test_data_gap_analysis.py::test_storage_offload_coverage_can_never_shrink`
