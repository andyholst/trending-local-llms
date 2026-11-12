# weight-gb-contrast-refusal

## ADDED Requirements

### Requirement: A measurement whose stated weight cannot belong to its model is refused at ingest

`ingest_raw_snapshots` MUST refuse, loudly and by name, a measurement whose stated `weight_gb`
contradicts the model's OWN weight footprint by more than `WEIGHTS_CONTRADICTION_FACTOR` — the
same bound `weights_gb()` draws — carrying the source post so a human can open the evidence. A
measurement with no `weight_gb`, or whose model has no own footprint, or whose ratio is within
the factor, MUST be kept (fail-open; never refuse what is not provable).

#### Scenario: the measured defect (Bonsai 2 9B carrying ~493GB NVFP4)

- **Given** the model `bonsai-2-9b` with own footprint `2.0GB (ternary)` and a measurement
  `MLX` 36 t/s whose `weight_gb` is `~493GB NVFP4` and whose `source_post` is
  `https://lightbrd.com/Chahatusharma/status/2111173528838103533`
- **When** `refuse_weight_gb_contradictions` is called on that model
- **Then** the measurement is refused, the reason names both the stated and the model-level
  footprint and the contradiction ratio, and the refusal carries the source post
- **Test:** tests/test_weight_gb_contradiction.py::test_the_shipped_bonsai_row_is_refused

#### Scenario: a stated footprint within the factor is kept

- **Given** a model with own footprint `2.0GB (ternary)` and a measurement whose `weight_gb`
  is `~5GB`
- **When** `refuse_weight_gb_contradictions` is called
- **Then** the measurement is kept (within `WEIGHTS_CONTRADICTION_FACTOR`)
- **Test:** tests/test_weight_gb_contradiction.py::test_a_footprint_within_the_factor_is_kept

#### Scenario: a measurement with no stated weight fails open

- **Given** a measurement whose row has no `weight_gb`
- **When** `refuse_weight_gb_contradictions` is called
- **Then** the measurement is kept (unknown proves nothing)
- **Test:** tests/test_weight_gb_contradiction.py::test_a_measurement_without_a_stated_weight_is_kept

#### Scenario: a model with no own footprint fails open

- **Given** a model whose own `weight_gb` is absent, and a measurement stating any weight
- **When** `refuse_weight_gb_contradictions` is called
- **Then** the measurement is kept (there is no own footprint to contradict)
- **Test:** tests/test_weight_gb_contradiction.py::test_a_model_without_its_own_footprint_is_kept

#### Scenario: the ingest wiring

- **Given** the `ingest_raw_snapshots` body
- **When** it is inspected
- **Then** it calls `refuse_weight_gb_contradictions(m, store)` before merging a row
- **Test:** tests/test_weight_gb_contradiction.py::test_the_ingest_wiring

### Requirement: the shipped store no longer carries a weight that cannot belong, and the scan reports any that sneak back

`make validate` MUST report — report-only, never fail — any store row whose measurement `weight_gb`
contradicts its model's own footprint, so a regression is loud rather than silent; and the shipped
store MUST NOT carry the measured Bonsai 2 9B `~493GB NVFP4` row after this change.

#### Scenario: the corrected store

- **Given** the shipped `data/measurements.json`
- **When** the store is read back
- **Then** `bonsai-2-9b` has no measurement with a `weight_gb` contradicting its own footprint
- **Test:** tests/test_weight_gb_contradiction.py::test_the_shipped_bonsai_row_is_corrected

#### Scenario: a regression is reported, never silent

- **Given** a store into which the build re-injects the Bonsai `~493GB NVFP4` measurement
- **When** `check_weight_gb_contradictions` runs
- **Then** it prints a WARN naming the model, the measurement and the source post, and the run
  still SUCCEEDS (report-only)
- **Test:** tests/test_weight_gb_contradiction.py::test_a_regression_is_reported_never_silent
