# ingest

## ADDED Requirements

### Requirement: A measured footprint is raised, never pinned and never shrunk

Merging two measurements of the same run MUST keep the **larger** stated figure for a numeric
dimension, MUST fill an unstated one, MUST NOT replace a stated text dimension, and MUST NOT store a
null.

#### Scenario: a later capture states a larger footprint

- **Given** a store row with `weight_gb: 5.93GB` and an incoming row for the same post with `5.95GB`
- **When** `merge_engines` merges them
- **Then** the row carries `5.95GB`, whichever order they arrive in
- **Test:** tests/test_7day_aggregation.py::test_a_measured_footprint_is_raised_never_pinned

#### Scenario: a smaller incoming value

- **Given** a store row with `5.95GB` and an incoming row with `5.13GB`
- **When** they are merged
- **Then** the store keeps `5.95GB` — a value is never shrunk
- **Test:** tests/test_7day_aggregation.py::test_a_measured_footprint_is_raised_never_pinned
