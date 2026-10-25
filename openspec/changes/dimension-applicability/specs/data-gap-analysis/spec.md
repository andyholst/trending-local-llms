# data-gap-analysis

## ADDED Requirements

### Requirement: A dimension that cannot apply is not counted missing

`analyse()` MUST consult a dimension's optional `applies` predicate and MUST report a model it
rejects under `not_applicable` rather than `missing`. A dimension with no predicate applies to
every model. The signature MUST name a dimension only while at least one applicable model lacks
a value.

#### Scenario: a dense small model cannot have a storage offload

- **Given** a 2B dense model with no storage-offload value
- **When** the store is analysed
- **Then** the model is in `not_applicable["storage_offload"]`, not in `missing`, and the
  render names it in the "cannot apply" section
- **Test:** tests/test_data_gap_analysis.py::test_a_dimension_that_cannot_apply_is_not_missing

#### Scenario: an applicable model without a value is still a gap

- **Given** an MoE (`35B-A3B`), a 70B dense model, and a model measured on Strata, none with a
  storage-offload value
- **When** the store is analysed
- **Then** all three are in `missing["storage_offload"]` and the signature carries
  `missing:storage_offload`
- **Test:** tests/test_data_gap_analysis.py::test_a_dimension_that_cannot_apply_is_not_missing

#### Scenario: a fully captured dimension leaves the signature

- **Given** a store whose only model states every dimension
- **When** the store is analysed
- **Then** no `missing:<dim>` entry survives in the signature
- **Test:** tests/test_data_gap_analysis.py::test_an_empty_dimension_never_reaches_the_signature
