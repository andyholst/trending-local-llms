# rulebook

## ADDED Requirements

### Requirement: The rulebook names every measurement dimension the store can hold

`AGENTS.md` §4 MUST list every optional per-measurement dimension the repository can hold,
and MUST NOT list one that no contract declares. The list of dimensions is derived from
the gap chain's registry (`data_gap_analysis.DIMENSIONS`) and the contracts' measurement
items — never restated as a second hand-maintained list.

#### Scenario: every tracked dimension is named

- **Given** `AGENTS.md` and the five dimensions `scripts/data_gap_analysis.py` ranks
- **When** the guard reads §4's optional-footprint sentence
- **Then** it names `weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload` and
  `engine_min_version`
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension

#### Scenario: the sentence names nothing the contracts refuse

- **Given** the names §4 lists for the optional footprint
- **When** the guard checks each against the measurement item of
  `data/model_contract.json` and `data/search_contract.json`
- **Then** every name is a property the contract declares (so §4 never documents a key the
  store prunes, rule 3b)
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension

#### Scenario: the registry has a key to store each dimension in

- **Given** `data_gap_analysis.DIMENSIONS`
- **When** the guard checks each key against both contracts' measurement items
- **Then** every tracked dimension has a measurement key in both contracts, so no ranked
  gap is one the store can never close
- **Test:** tests/test_measurement_footprint.py::test_the_rulebook_names_every_measurement_dimension
