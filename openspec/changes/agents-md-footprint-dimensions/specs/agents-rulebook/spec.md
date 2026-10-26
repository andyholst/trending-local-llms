# agents-rulebook

## ADDED Requirements

### Requirement: §4 names every optional per-measurement footprint dimension

`AGENTS.md` §4's `data/models.json` bullet MUST name every optional
per-measurement footprint dimension the store contract can hold — today
`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload` and
`engine_min_version` — and MUST say the keys are additive and never `required`.
`tests/test_agents_rows.py` MUST derive that key set from
`data/model_contract.json` and fail when the sentence omits one, so a dimension
declared by the contract cannot stay unmentioned in the rulebook.

#### Scenario: the sentence names the fifth dimension

- **Given** `data/model_contract.json`, whose measurement object declares
  `engine_min_version` OPTIONAL beside the four footprints the sentence already
  carried
- **When** §4's footprint sentence is read
- **Then** it names `weight_gb`, `context_tokens`, `system_ram_min`,
  `storage_offload` and `engine_min_version`, keeps the "additive, never
  required" clause and cites `#337` and `#371`
- **Test:** tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension

#### Scenario: a contract dimension the rulebook forgets fails the suite

- **Given** a footprint dimension added to BOTH the model row and the
  measurement object of `data/model_contract.json` (the shape the family has)
- **When** `make test` runs and §4's sentence does not name it
- **Then** the pin fails naming the missing dimension, instead of the rulebook
  going quiet again
- **Test:** tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension
