## ADDED Requirements

### Requirement: Model-level footprint copies trace to captured data

Every model-level footprint value in `data/models.json` for a HARD field
(`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`) MUST be
traceable: it either matches one of that model's own measurement rows, or
matches a footprint value captured for the same model in `data/raw/*.json`, or
carries the canonical `(est)` marker. A value that matches neither and carries
no marker FAILS `make validate`. Matching uses one shared implementation
(normalized containment, figure-token intersection, and K/M suffix expansion so
`200000` matches `200K`). `engine_min_version` copies are report-only, per the
#789 split precedent.

#### Scenario: model-level value matching a measurement row passes

- **Given** a model whose `weight_gb` equals the `weight_gb` of one of its own measurement rows
- **When** `make validate` runs the `data` stage
- **Then** `check_model_footprint_copy` reports it as row-traced and no failure is recorded
- **Test:** tests/test_model_footprint_copy.py::test_row_match_passes

#### Scenario: model-level value captured in the model's raw snapshots passes

- **Given** a model-level `system_ram_min` that no measurement row carries but a row-level capture for the same model in `data/raw` states
- **When** the check runs
- **Then** it passes via the capture pool
- **Test:** tests/test_model_footprint_copy.py::test_capture_match_passes

#### Scenario: K-suffix notation is the same figure

- **Given** a model-level `context_tokens` of `200000` and a measurement row stating `200K`
- **When** the check runs
- **Then** the value passes (no orphan flag) through the K/M expansion
- **Test:** tests/test_model_footprint_copy.py::test_ksuffix_expansion_passes

#### Scenario: an untraceable unmarked copy fails the gate

- **Given** a planted model-level `weight_gb` that matches no measurement row, no raw capture of the model, and carries no `(est)` marker
- **When** the check runs
- **Then** it records a failure naming the model, field and value
- **Test:** tests/test_model_footprint_copy.py::test_untraceable_copy_fails

#### Scenario: an (est)-marked copy is attributed, not flagged

- **Given** a planted model-level `weight_gb` ending in the canonical `(est)` marker, matching nothing
- **When** the check runs
- **Then** no failure is recorded (a marked value is a declared estimate)
- **Test:** tests/test_model_footprint_copy.py::test_est_marker_passes

#### Scenario: engine_min_version copies are report-only

- **Given** a planted model-level `engine_min_version` matching no row or capture
- **When** the check runs
- **Then** it appears in the report and records NO failure
- **Test:** tests/test_model_footprint_copy.py::test_prose_field_report_only

#### Scenario: the shipped store holds zero untraceable unmarked hard copies

- **Given** the shipped `data/models.json` and `data/raw/`
- **When** the shipped-store gate runs
- **Then** `model_level_footprint_flags` returns no HARD flag
- **Test:** tests/test_model_footprint_copy.py::test_shipped_store_has_no_untraceable_hard_copy
