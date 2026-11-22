## ADDED Requirements

### Requirement: Read-only derived type rollup

The report SHALL derive a `type_group` from each shipped `type` label using one mapping table, SHALL join measurements by model id and declared aliases, and SHALL print model count, measurement count, engine count, architecture count, newest date and median t/s per group. It SHALL NOT write either store. An unseen label SHALL be reported as `unknown` with its name, never silently bucketed.

#### Scenario: Two labels for one architecture

- **WHEN** `LLM (MoE)` and `MoE LLM` models are in the store
- **THEN** both are counted in the `moe` group

#### Scenario: Unknown label

- **WHEN** a new `type` value appears in the store
- **THEN** it appears under `unknown` and is named in the report

#### Scenario: Store write attempted

- **WHEN** the rollup code writes to models.json or measurements.json
- **THEN** `tests/test_model_type_rollup.py` fails
