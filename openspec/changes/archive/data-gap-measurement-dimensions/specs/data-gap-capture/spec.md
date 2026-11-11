# data-gap-capture

## ADDED Requirements

### Requirement: A captured dimension survives the measurement merge

When `merge_engines` collapses concordant rows into one representative, every
OPTIONAL requirement dimension (`weight_gb`, `context_tokens`, `system_ram_min`,
`storage_offload`, `engine_min_version`) carried by ANY member of the group MUST
be present on the representative — fill-only, so a value the representative (or
the store row it came from) already holds is never overwritten and a dimension no
member states is never invented.

#### Scenario: the representative lacks the dimension another member states

- **Given** a store measurement and an incoming raw measurement of the same engine, GPU size and t/s, where the store row wins the group as representative and the incoming row is the only one stating `weight_gb` / `context_tokens` / `system_ram_min`
- **When** the real ingest merges the raw snapshot into the store
- **Then** the representative measurement carries those dimension values, the store's own missing keys are filled, and no other measurement or value is changed
- **Test:** tests/test_measurement_footprint.py::test_a_dimension_survives_the_merge_onto_an_existing_measurement

#### Scenario: an incoming row must not drop a stored dimension

- **Given** a store measurement that states `storage_offload` and an incoming raw measurement of the same measurement with higher engagement (so it becomes the representative) that states no `storage_offload`
- **When** the real ingest merges the raw snapshot into the store
- **Then** the stored `storage_offload` is still on the merged row — the merge never shrinks a value (AGENTS.md rule 3b)
- **Test:** tests/test_measurement_footprint.py::test_the_merge_never_drops_a_stored_dimension

### Requirement: Every per-measurement dimension traces to the captured post

A measurement-level dimension value in the store MUST appear verbatim in the
captured text of the model's source snapshots in `data/raw/*.json`. A value no
captured snapshot states is a fabrication and MUST fail the suite.

#### Scenario: the store's measurement dimensions are all in the captured text

- **Given** the real store and the real raw search snapshots
- **When** the traceability guard runs
- **Then** every measurement-level `weight_gb` / `context_tokens` / `system_ram_min` / `storage_offload` / `engine_min_version` value appears verbatim in that model's captured raw text
- **Test:** tests/test_data_gap_analysis.py::test_measurement_dimensions_trace_to_the_captured_snapshot

### Requirement: The backfilled coverage cannot silently shrink

The number of measurements carrying at least one structured dimension MUST stay
at or above the floor this change establishes, so a regeneration that drops the
backfill turns the suite red.

#### Scenario: coverage floor holds on the real store

- **Given** the real store after this change
- **When** the coverage guard runs
- **Then** at least 43 measurements carry a structured dimension
- **Test:** tests/test_data_gap_analysis.py::test_measurement_dimension_coverage_can_never_shrink
