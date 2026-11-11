# measurement-ingest Specification

## Purpose
TBD - created by archiving change joint-comparison-figure. Update Purpose after archive.

## Requirements

### Requirement: A joint comparison figure is refused at ingest
A measurement whose own text names a same-family model of a different parameter
size than the row AND carries exactly one t/s figure SHALL be refused at ingest
as a joint figure, with the refusal naming both identities and the source post.
Two or more t/s figures SHALL be kept as one-figure-per-model; a comparison cue
with no t/s figure SHALL keep its existing rescue.

#### Scenario: The issue's own example is refused
- **Given** a `Qwen 3.6 27B` row
- **When** a measurement's `quant` reads "Qwen 3.6 27B vs Qwen 3.5 35B: 140 t/s"
- **Then** `refuse_misattributed_measurements` refuses it with a joint-figure reason
- **Test:** tests/test_measurement_attribution.py::test_a_joint_comparison_figure_is_refused

#### Scenario: A per-model bake-off is kept
- **Given** the same row
- **When** the `quant` reads "Qwen 3.6 27B 90 t/s vs Qwen 3.5 35B 40 t/s"
- **Then** the measurement is kept (one figure per model)
- **Test:** tests/test_measurement_attribution.py::test_one_figure_per_model_is_kept

#### Scenario: A cue without any figure keeps its rescue
- **Given** the same row
- **When** the `quant` reads "Qwen 3.6 27B vs Qwen 3.5 35B on the same card"
- **Then** the measurement is kept (unchanged behaviour)
- **Test:** tests/test_measurement_attribution.py::test_a_comparison_cue_is_kept
