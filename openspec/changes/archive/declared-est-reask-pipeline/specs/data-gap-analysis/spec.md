# data-gap-analysis

## ADDED Requirements

### Requirement: A declared estimate is a named, re-askable class

The analysis MUST read the `(est)` / `(estimated)` marker through the ONE
detector (`scripts/declared_estimate.py`) and report every footprint value that
carries it as `declared_estimates` — `field -> model/engine:field=value`
entries, from measurements AND model rows — with the class named in the report,
in the gap-issue body, and in the signature once per field. A measured value
MUST never enter the class.

#### Scenario: a footprint value carries the marker

- **Given** a model whose `weight_gb` measurement reads `14.6 (est)` and whose model-row `engine_min_version` reads `llama.cpp b9100 (estimated)`
- **When** the store is analysed
- **Then** both values appear in `declared_estimates` naming model+field, the signature carries exactly the two `reask_estimate:<field>` entries, and the report and issue body each name them
- **Test:** tests/test_data_gap_analysis.py::test_declared_estimates_surface_as_a_reaskable_class

#### Scenario: a measured value is never re-askable material

- **Given** a model whose only footprint values are unmarked (`weight_gb` 5.9)
- **When** the store is analysed
- **Then** `declared_estimates` is empty, no `reask_estimate:` signature entry exists, and the report section says `- none`
- **Test:** tests/test_data_gap_analysis.py::test_declared_estimates_surface_as_a_reaskable_class

### Requirement: The marker has exactly one detector

The `(est)` marker pattern and the footprint field set MUST be defined once, in
`scripts/declared_estimate.py`, whose `FOOTPRINT_FIELDS` are byte-identical
(order included) to the analysis's `DIMENSIONS` keys; `data_gap_analysis.py`
MUST import it and MUST NOT carry a marker regex of its own.

#### Scenario: a stage tries to keep its own copy of the marker

- **Given** `scripts/declared_estimate.py` as the only holder of the pattern
- **When** the guard reads the analysis source and both field lists
- **Then** the analysis imports the module, contains no `(?:est|estimated)` literal, and the module's field set equals `DIMENSIONS` exactly
- **Test:** tests/test_data_gap_analysis.py::test_the_declared_estimate_detector_is_one_detector
