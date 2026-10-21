# measurement-source-dimensions

## ADDED Requirements

### Requirement: A requirement dimension the measurement is the home of is accepted there

Both contracts (`data/search_contract.json`, `data/model_contract.json`) MUST
declare `engine_min_version` as an OPTIONAL string on the measurement item —
additively, never in `required` — because a minimum engine build or a set of
required flags is a property of the ENGINE THAT RAN THE FIGURE and not of the
model: one model measured on two engines carries two different ones. A search
snapshot that records it per measurement MUST validate.

WHEN a search leg records the engine build or the flags a figure reproduces on
against the measurement that produced it,
THEN the snapshot conforms to the search contract and the store conforms to the
model contract.

#### Scenario: the search contract accepts a per-measurement engine_min_version

- **Given** a raw search snapshot whose measurement carries `engine_min_version` (the shape measured on run 39124432576) and nothing else changed
- **When** the real `check_search_contract` runs against the real `data/search_contract.json`
- **Then** it reports no failure — the pre-change contract reports `Additional properties are not allowed ('engine_min_version' was unexpected) (at ['models', 0, 'engines', 1])`
- **Test:** `make test` → `python3 tests/test_measurement_footprint.py`, block `test_the_search_contract_accepts_a_per_measurement_engine_min_version` (rule 6d: the script is wired into `make _test`; pytest is not in the test image, so the blocks are the tests)

#### Scenario: the key is additive in both contracts

- **Given** both contract files
- **When** the measurement item is read
- **Then** `engine_min_version` is one of its `properties` and is NOT one of its `required` entries, so old snapshots still validate
- **Test:** `make test` → `python3 tests/test_measurement_footprint.py`, block `test_the_contract_declares_them_optional`

### Requirement: The value survives ingest onto the measurement

Ingest MUST carry a measurement's `engine_min_version` into the store unchanged
and MUST coerce a bare number to its text form by the same rule the model-level
dimensions use, and MUST NOT invent one: a post that states no build leaves the
measurement without the key. The key MUST be named by the ONE definition of the
per-measurement optional dimensions,
`update_trending.MEASUREMENT_DIMENSION_FIELDS`.

WHEN a raw snapshot is ingested,
THEN every measurement dimension it states is on the store's measurement and
every one it does not state is absent.

#### Scenario: a stated engine build reaches the store measurement

- **Given** a raw snapshot whose measurement states `engine_min_version`
- **When** the real ingest runs
- **Then** the store's measurement carries that exact value, its t/s is unchanged, and the store validates against the real `model_contract.json`
- **Test:** `make test` → `python3 tests/test_measurement_footprint.py`, block `test_a_measurement_footprint_survives_ingest`

#### Scenario: an absent engine build is never invented

- **Given** a raw snapshot whose measurements state no per-run dimension
- **When** the real ingest runs
- **Then** no measurement carries `engine_min_version`, because an absent figure is a reported data gap and an invented one is a fabrication
- **Test:** `tests/test_fixture_mapping.py::test_optional_fields_filled`

### Requirement: The prompt asks for the dimension where it belongs

The search prompt (`Makefile` `DIM_ASK`, embedded in every leg) MUST ask for
`engine_min_version` among the dimensions to record ON the measurement, so a leg
is never left choosing between the model row the contract accepted and the
measurement where the figure belongs.

WHEN a search leg reads the dimension ask,
THEN it is told the engine build or the flags THAT run needed go on the
measurement.

#### Scenario: the ask names the measurement for the build and flags

- **Given** the Makefile's `DIM_ASK` string
- **When** every leg's prompt is composed
- **Then** the ask names `engine_min_version` as a measurement-level dimension, alongside `weight_gb`, `context_tokens`, `system_ram_min` and `storage_offload`
- **Test:** `tests/test_hermes_prompts.py::test_every_search_leg_asks_for_the_model_dimensions_from_one_definition`
