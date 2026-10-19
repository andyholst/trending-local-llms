# data-gap-analysis

## ADDED Requirements

### Requirement: A dimension captured on a measurement counts as captured

`analyse()` MUST treat a dimension as stored when the model row OR any of its measurements
carries a non-empty value, and MUST report `unstructured` only when neither does.

#### Scenario: the value lives only on a measurement

- **Given** a model whose only `storage_offload` is on one of its measurements, and a sibling that states it nowhere
- **When** the store is analysed
- **Then** the measured model is neither `missing` nor `unstructured`, the sibling is both reported as missing and named in the signature
- **Test:** tests/test_data_gap_analysis.py::test_a_measurement_level_value_is_captured

#### Scenario: free text is still not a stored value

- **Given** a model whose only RAM figure is the string `"1432 MB peak RAM"` inside `quant`
- **When** the store is analysed
- **Then** it is reported as free-text-only and still counts as missing
- **Test:** tests/test_data_gap_analysis.py::test_free_text_mention_is_unstructured_not_present
