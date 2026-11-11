# validate-source-post-readback

## ADDED Requirements

### Requirement: `make validate` re-reads a measurement's captured source post

`make validate` MUST run a scan that, for every store measurement whose `source_post` appears
in `data/raw/*`, re-derives the stated footprint dimension values (`weight_gb`,
`context_tokens`, `system_ram_min`, `storage_offload`, `engine_min_version`) from the captured
text and flags a stored value that appears in NEITHER the capture's structured fields NOR the
captured post text. The scan MUST be report-only (it never fails `validate` on a parser miss),
so its precision can be measured on the store as it stands before a later change turns it into
a gate.

#### Scenario: a stored value the captured post states is kept

- **Given** a store measurement whose `source_post` is `…/status/1`, whose `weight_gb` is
  `5.95GB`, and a `data/raw` snapshot capture of that post whose `quant` reads
  `PTQ1_0 ternary (5.95 GB weights)`
- **When** the source-post readback scan runs
- **Then** the measurement is NOT flagged (the stored figure appears in the captured text once
  spacing is normalised)
- **Test:** tests/test_source_post_readback.py::test_a_stored_value_the_capture_states_is_kept

#### Scenario: a stored value the captured post nowhere states is flagged

- **Given** a store measurement whose `source_post` is `…/status/2`, whose `weight_gb` is
  `5.93GB`, and a `data/raw` capture of that post whose `quant` reads `5.95GB ternary (PTQ1_0)`
- **When** the source-post readback scan runs
- **Then** the measurement IS flagged, naming the model, the engine, the field, the stored
  value and the post
- **Test:** tests/test_source_post_readback.py::test_a_contradicted_stored_value_is_flagged

#### Scenario: a captured structured field confirms a value the free text lacks

- **Given** a store measurement whose `context_tokens` is `262144` and whose `source_post` has
  a capture whose structured `context_tokens` field carries `262144` while the free text states
  no window
- **When** the scan runs
- **Then** the measurement is NOT flagged (the value appears in the capture's own structured
  fields)
- **Test:** tests/test_source_post_readback.py::test_a_value_in_the_capture_structured_field_is_kept

#### Scenario: a measurement whose post is not captured is skipped

- **Given** a store measurement whose `source_post` appears in NO `data/raw/*.json` snapshot
- **When** the scan runs
- **Then** the measurement is not checked (there is no captured text to re-derive from)
- **Test:** tests/test_source_post_readback.py::test_an_uncaptured_post_is_skipped

#### Scenario: the scan is report-only on the store as it stands

- **Given** the shipped store, which holds a handful of footprint values the captures do not
  restate
- **When** `make validate` runs the `data` stage
- **Then** the scan prints a WARN listing the unsupported values and adds NO failure — a red on
  history the scan cannot repair is exactly what the report-only first cut avoids
- **Test:** tests/test_source_post_readback.py::test_the_scan_is_report_only_it_never_fails
