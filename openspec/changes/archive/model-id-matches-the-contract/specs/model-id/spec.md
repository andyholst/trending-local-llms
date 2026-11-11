# model-id

## ADDED Requirements

### Requirement: A written model id satisfies the store contract

`--write-raw` MUST write an id that matches `^[a-z0-9][a-z0-9.\-]*$`, normalising one that does
not (lowercase, `_`/space → `-`, only `[a-z0-9.-]`), so a raw snapshot can never fail
`search_contract` on the id it records.

#### Scenario: the measured underscore

- **Given** a raw payload carrying `id: "qwen3.8-27b-mlx_srv"`
- **When** the snapshot is written
- **Then** the file carries `qwen3.8-27b-mlx-srv` and that matches the contract pattern
- **Test:** tests/test_search_budget.py::test_the_model_id_matches_the_contract

### Requirement: Ingest never hands the store an illegal id

`normalize_model` MUST normalise a provided id that violates the pattern before the model is
stored, and MUST leave an id that already matches byte-identical, so no stored key is renamed
(rule 3b).

#### Scenario: a raw row that predates the rule

- **Given** a raw model with `id: "qwen3.8-27b-mlx_srv"`
- **When** it is normalised at ingest
- **Then** the stored id is `qwen3.8-27b-mlx-srv`
- **Test:** tests/test_search_budget.py::test_the_model_id_matches_the_contract

#### Scenario: an id that is already legal

- **Given** a raw model with `id: "qwen3.8-27b"`
- **When** it is normalised at ingest
- **Then** the id is unchanged
- **Test:** tests/test_search_budget.py::test_the_model_id_matches_the_contract
