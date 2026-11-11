# data-gap-backfill

## ADDED Requirements

### Requirement: A captured footprint is never lost from the store

Every requirement-dimension value a captured per-backend snapshot
(`data/raw/*.json`, the record of a real `…/status/<id>` post) states for a run
MUST be carried by the store measurement the snapshot recorded it for — matched
by model id, `source_post` AND engine, so a value is never copied across models.
The guard MUST fail when such a value is absent, and MUST be non-vacuous on the
real store.

WHEN the store is compared with the captured snapshots,
THEN no captured dimension cell is missing from its matching store measurement.

#### Scenario: the store carries every captured cell

- **Given** the real store and the real `data/raw/*.json` snapshots
- **When** the capture guard runs
- **Then** every `(model id, source_post, engine)` cell a snapshot states is present on the matching store measurement(s), and the guard has compared at least one real cell
- **Test:** `tests/test_data_gap_analysis.py::test_a_captured_measurement_footprint_is_never_lost_from_the_store`

#### Scenario: a store that dropped the value fails the guard

- **Given** an in-memory copy of the store with a captured dimension value removed from its measurement
- **When** the capture guard runs
- **Then** it reports that cell as lost and fails
- **Test:** `tests/test_data_gap_analysis.py::test_a_captured_measurement_footprint_is_never_lost_from_the_store`

### Requirement: A captured value the legs disagree on is satisfied, never guessed

Several legs may capture the same run with different wording. The guard MUST
accept ANY of the wordings the captured post states and MUST NOT require one of
them to win, so a disagreement never forces an invented single value.

WHEN two captured legs state different wordings for one cell,
THEN the store satisfies the guard by carrying either wording.

#### Scenario: a disagreement is satisfied by either wording

- **Given** a captured cell whose legs state `64GB (developer recommendation; tested on 128GB)` and `64GB recommended (128GB DDR4-2400 tested)`
- **When** the guard runs against the store
- **Then** the cell counts as carried, and the store's value is one of the two captured wordings
- **Test:** `tests/test_data_gap_analysis.py::test_a_captured_measurement_footprint_is_never_lost_from_the_store`

### Requirement: The per-dimension capture cannot silently shrink

The measurements carrying a structured requirement dimension MUST be asserted
against a floor, per dimension, so a regeneration that loses one dimension's
capture turns the suite red even while the other four still pass.

WHEN the store is regenerated without a dimension's backfill,
THEN the coverage guard fails naming that dimension.

#### Scenario: the total and per-dimension floors hold

- **Given** the real store after this change
- **When** the coverage guard runs
- **Then** at least 46 measurements carry a structured dimension, and each of `weight_gb` (26), `context_tokens` (18), `system_ram_min` (24), `storage_offload` (2) and `engine_min_version` (14) meets its own floor
- **Test:** `tests/test_data_gap_analysis.py::test_measurement_dimension_coverage_can_never_shrink`
