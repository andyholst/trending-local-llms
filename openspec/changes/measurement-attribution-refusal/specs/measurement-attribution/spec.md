# measurement-attribution

## ADDED Requirements

### Requirement: A measurement names the model of the row it is merged into

At ingest, a measurement whose `quant` or `why` text names a model of the SAME family
with a DIFFERENT parameter size than the row it would merge into MUST be refused, loudly,
with the source post named. A comparison cue (`vs`, `versus`, `compared`, `baseline`,
`than`, `beats`, `against`, `not the`, `instead of`, `while`), a mention of the row's own
model in the same text, a cross-family mention, an unparseable row identity, and an
explicit `MEASUREMENT_MODEL_ALIASES` entry MUST keep the measurement.

#### Scenario: the measured defect

- **Given** a row `Qwen 3.6 27B` and a measurement whose `quant` reads "Qwen 3.5 35B served
  through LM Studio anthropic-compatible endpoint (v1/messages), 80k context, model fully
  in VRAM"
- **When** `refuse_misattributed_measurements` is called on that row
- **Then** the measurement is refused, the reason names both identities, and the refusal
  carries the source post
- **Test:** tests/test_measurement_attribution.py::test_the_reported_measurement_is_refused

#### Scenario: the row's own model is named in a multi-model post

- **Given** a row `Qwen 3.6 27B` and a measurement whose `quant` names both `Qwen3.6 27B`
  and `Qwen 3.6 35B`
- **When** the refusal check runs
- **Then** the measurement is kept (the post measures this row's model too)
- **Test:** tests/test_measurement_attribution.py::test_a_multi_model_post_naming_the_row_is_kept

#### Scenario: a comparison sentence

- **Given** a measurement whose `quant` reads "Qwen 3.6 27B vs Qwen 3.5 35B on the same card"
- **When** the refusal check runs
- **Then** the measurement is kept (a comparison is not a misattribution)
- **Test:** tests/test_measurement_attribution.py::test_a_comparison_cue_is_kept

#### Scenario: a cross-family mention

- **Given** a row `Qwen 3.6 27B` and a measurement naming `Gemma 4 26B`
- **When** the refusal check runs
- **Then** the measurement is kept (cross-family mentions are context)
- **Test:** tests/test_measurement_attribution.py::test_a_cross_family_mention_is_kept

#### Scenario: an explicit alias mapping documents an exception

- **Given** a row whose identity cannot distinguish a legitimate exception
- **When** `MEASUREMENT_MODEL_ALIASES` names that row's permitted counterpart
- **Then** the measurement is kept; without the mapping it is refused
- **Test:** tests/test_measurement_attribution.py::test_an_explicit_alias_mapping_documents_an_exception

#### Scenario: an unparseable row identity fails open

- **Given** a variant row whose name puts words between the version and the size
  (`Qwen3.8-Flash-Next 125B`)
- **When** the refusal check runs
- **Then** the measurement is kept (the guard never guesses a refusal from a name it could
  not parse)
- **Test:** tests/test_measurement_attribution.py::test_an_unknown_identity_fails_open

### Requirement: The ingest seam calls the refusal, and the shipped row is reported

`ingest_raw_snapshots` MUST call `refuse_misattributed_measurements` where a raw row merges,
and `make validate` MUST report — report-only — the historical rows the ingest refusal
cannot repair.

#### Scenario: the ingest wiring

- **Given** the `ingest_raw_snapshots` body
- **When** it is inspected
- **Then** it calls `refuse_misattributed_measurements(m, store)` before merging
- **Test:** tests/test_measurement_attribution.py::test_ingest_calls_the_refusal

#### Scenario: a new row whose only measurement is refused

- **Given** a raw snapshot introducing a model whose sole measurement names another model
- **When** `ingest_raw_snapshots` merges it
- **Then** the model is NOT stored (an empty row would fail `check_model_fields`), the
  refusal is loud, and the rest of the snapshot still merges
- **Test:** tests/test_measurement_attribution.py::test_ingest_drops_a_new_row_whose_only_measurement_is_refused

#### Scenario: the shipped store's misplaced figure

- **Given** the shipped `data/models.json`
- **When** `validate --only data` runs
- **Then** the attribution scan prints the `qwen-3.6-27b` row as a WARN and the run still
  SUCCEEDS
- **Test:** tests/test_measurement_attribution.py::test_the_shipped_store_reports_the_known_row
