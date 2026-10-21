# data-gap-baseline

## ADDED Requirements

### Requirement: A gap dimension files once, not once per model

The issue-triggering signature MUST contain one entry per DIMENSION
(`contract:<key>` / `missing:<key>` / `unstructured:<key>`), so a model that joins an existing
gap does not make the gap set look new and the filer does not re-file the same dimension.

#### Scenario: a model joins an existing gap

- **Given** a store whose one model lacks `system_ram_min`
- **When** a second model with the same gap is analysed
- **Then** the signature is unchanged, and both models are still named in the report
- **Test:** tests/test_data_gap_analysis.py::test_signature_tracks_the_store_not_the_noise

#### Scenario: the measured re-file loop

- **Given** a baseline recorded for a store with one model
- **When** more models with the SAME gaps are analysed
- **Then** `--check` stays 0 — no new issue — which is what stopped the twelve `storage_offload` filings
- **Test:** tests/test_data_gap_analysis.py::test_write_baseline_records_the_signature_without_filing

### Requirement: A real change to the gap set still files

A signature that gains or loses an entry MUST still be reported as a change, so a genuinely new
dimension is filed and `--check` exits 1.

#### Scenario: a baseline carrying an entry the store no longer has

- **Given** a baseline whose signature carries an entry the current store does not produce
- **When** the analysis runs with `--check`
- **Then** it exits 1, and a report-only run still exits 0
- **Test:** tests/test_data_gap_analysis.py::test_write_baseline_records_the_signature_without_filing
