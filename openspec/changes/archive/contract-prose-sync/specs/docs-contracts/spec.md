# docs-contracts

## ADDED Requirements

### Requirement: Every model contract property has a prose row

`scripts/check_contract_prose.py` SHALL parse the pipe-table rows of `data/MODEL_CONTRACT.md`
(`| \`field\` | yes/no | meaning |`) and compare them to `data/model_contract.json`'s
`properties.models.items`. Every schema property SHALL have a row; a row naming a property the
schema does not declare SHALL fail as unknown. The Meaning cell is prose and SHALL NOT be parsed.

#### Scenario: a schema property with no prose row

- **Given** a contract JSON property with no row in `data/MODEL_CONTRACT.md`
- **When** `scripts/check_contract_prose.py` runs
- **Then** it FAILS naming the property and saying there is no row
- **Test:** tests/test_contract_prose.py::test_a_schema_property_without_a_prose_row_is_red

#### Scenario: an unknown prose row

- **Given** an MD row naming a property the schema does not declare
- **When** the check runs
- **Then** it FAILS naming the undeclared row
- **Test:** tests/test_contract_prose.py::test_a_schema_property_without_a_prose_row_is_red

### Requirement: Required-ness agrees in both directions

Every row's Required cell SHALL equal membership in the schema's `required` array. A cell that
disagrees SHALL fail naming BOTH sides (what the prose says and what the schema requires), in
either direction, and a cell outside `yes`/`no` SHALL be refused rather than read as drift.

#### Scenario: the prose marks optional a field the schema requires

- **Given** a property in the schema `required` array whose MD row reads `no`
- **When** the check runs
- **Then** it FAILS naming the property and stating that the schema REQUIRES it
- **Test:** tests/test_contract_prose.py::test_required_disagreement_is_red_in_both_directions

#### Scenario: the prose marks required a field the schema does not require

- **Given** a property not in the schema `required` array whose MD row reads `yes`
- **When** the check runs
- **Then** it FAILS naming the property and stating that the schema does NOT require it
- **Test:** tests/test_contract_prose.py::test_required_disagreement_is_red_in_both_directions

### Requirement: The shipped tree is green

After the additive row fix, the real pair SHALL pass and the stage SHALL print the property and
row counts.

#### Scenario: the real store and contract

- **Given** the shipped tree at the fixed head
- **When** `python3 scripts/check_contract_prose.py` (and the validator's `docs` stage) runs
- **Then** it exits 0, prints the property count and the row count, and every Required cell matches
- **Test:** tests/test_contract_prose.py::test_the_real_store_and_contract_are_green

### Requirement: The check is wired to a stage and a target

`check_contract_prose()` SHALL be registered in `scripts/validate.py` under a NEW stage `docs`,
reachable from `_validate` (all stages) and selected by the existing `_validate-schema` target's
`--only schema,docs`.

#### Scenario: the wiring guard

- **Given** the new check
- **When** the validator's stage map and the Makefile `--only` lists are read
- **Then** `docs` is registered AND selected by a Makefile `--only` list, and `--only docs` executes it
- **Test:** tests/test_contract_prose.py::test_the_check_is_wired_to_a_stage_and_a_target
