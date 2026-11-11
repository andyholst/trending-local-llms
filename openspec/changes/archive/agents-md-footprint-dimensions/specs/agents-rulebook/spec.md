# agents-rulebook

## ADDED Requirements

### Requirement: §4 names every optional per-measurement footprint dimension

`AGENTS.md` §4's `data/models.json` bullet MUST name every optional
per-measurement footprint dimension the store contract can hold — today
`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload` and
`engine_min_version` — and MUST say the keys are additive and never `required`.
`tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension`
MUST derive that key set from `scripts/data_gap_analysis.py`'s `DIMENSIONS` and
the contracts' measurement items, and fail when the sentence omits one, so a
dimension declared by the contract cannot stay unmentioned in the rulebook.

#### Scenario: the sentence names the fifth dimension

- **Given** `data/model_contract.json`, whose measurement object declares
  `engine_min_version` OPTIONAL beside the four footprints the sentence already
  carried
- **When** §4's footprint sentence is read
- **Then** it names `weight_gb`, `context_tokens`, `system_ram_min`,
  `storage_offload` and `engine_min_version`, keeps the "additive, never
  required" clause and cites `#337` and `#371`
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension

#### Scenario: a contract dimension the rulebook forgets fails the suite

- **Given** a footprint dimension added to BOTH the model row and the
  measurement object of `data/model_contract.json` (the shape the family has)
- **When** `make test` runs and §4's sentence does not name it
- **Then** the pin fails naming the missing dimension, instead of the rulebook
  going quiet again
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension

#### Scenario: the sentence names nothing the contracts refuse

- **Given** the dimension names §4 lists for the optional footprint
- **When** the pin checks each name against the measurement item of
  `data/model_contract.json` and `data/search_contract.json`
- **Then** every name is a property the contract declares, so the rulebook never
  documents a key ingest would prune (rule 3b)
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension

#### Scenario: every ranked gap dimension has a key to be stored in

- **Given** `scripts/data_gap_analysis.py`'s `DIMENSIONS`
- **When** the pin checks each key against both contracts' measurement items
- **Then** every tracked dimension has a measurement key in both contracts, so no
  ranked gap is one the store can never close
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension
