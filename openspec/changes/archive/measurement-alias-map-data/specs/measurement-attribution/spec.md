# Spec delta: measurement-attribution (measurement-alias-map-data)

## ADDED Requirements

### Requirement: A documented attribution exception is data on the model row
The attribution exception mapping SHALL live in the store as the optional model-row
key `measurement_model_aliases` (array of store model ids), declared in
`data/model_contract.json` additively and never required; the ingest reader SHALL
resolve it from the incoming row and the same-id store row, and no code literal
may hold attribution exceptions.

#### Scenario: an alias declared on the row keeps the measurement
- **Given** a store row `bonsai-2-9b` whose `measurement_model_aliases` lists `bonsai-2-27b`
- **When** an incoming measurement on `bonsai-2-9b` names `Bonsai 2 27B` in its own text
- **Then** the measurement is kept, not refused as a misattribution
- **Test:** tests/test_measurement_attribution.py::test_an_explicit_alias_mapping_documents_an_exception

#### Scenario: without the data key the same measurement is refused
- **Given** the same rows with no `measurement_model_aliases` key anywhere
- **When** the same measurement is ingested
- **Then** it is refused with a reason that names the data key
- **Test:** tests/test_measurement_attribution.py::test_an_explicit_alias_mapping_documents_an_exception

#### Scenario: the code dictionary is gone
- **Given** `scripts/update_trending.py` after this change
- **When** the tree is searched for an attribution exception literal
- **Then** `MEASUREMENT_MODEL_ALIASES` appears nowhere and the reader uses the row key
- **Test:** tests/test_measurement_attribution.py::test_attribution_exceptions_live_in_data_not_code

### Requirement: A dangling alias counterpart fails validation
`make validate` SHALL fail when a model row lists a `measurement_model_aliases`
counterpart id that is not a model id in the store — a dangling alias must never
sit in the store as a silent no-op.

#### Scenario: a valid counterpart validates
- **Given** a store whose alias counterparts all exist as model ids
- **When** `make validate` runs the mapping stage
- **Then** validation passes
- **Test:** tests/test_validate.py::test_measurement_alias_map_gate_accepts_resolvable_aliases

#### Scenario: a dangling counterpart is refused loudly
- **Given** a store where a row aliases a model id that is not in the store
- **When** the mapping stage runs
- **Then** validation fails naming the row and the dangling id
- **Test:** tests/test_validate.py::test_measurement_alias_map_gate_refuses_a_dangling_alias

#### Scenario: the gate is wired to a stage and a make target
- **Given** `check_measurement_alias_map` registered in the validate stage map
- **When** the wiring guard runs
- **Then** the mapping stage's Makefile `--only` lists select it
- **Test:** tests/test_validate.py::test_every_check_is_wired_to_a_stage_and_a_makefile_target
