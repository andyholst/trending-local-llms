# data-gap-analysis

## ADDED Requirements

### Requirement: A missing dimension says whether a post ever stated it

`analyse()` MUST classify every model missing a dimension against the text the search
CAPTURED for it in `data/raw/*.json` (resolved to the store id by the one resolver), and MUST
report the models whose captured posts state no such figure as “not stated by any captured
post” — an ACQUISITION gap — separately from the models whose captured or stored prose states
it and the store holds no structured value — an INGEST gap.

#### Scenario: a model whose capture states nothing is an acquisition gap

- **Given** a store model with no structured `context_tokens` and a captured snapshot that
  states no context window for it
- **When** the store is analysed
- **Then** the model is listed under the un-captured class for that dimension and NOT counted
  as an ingest gap
- **Test:** tests/test_data_gap_analysis.py::test_an_acquisition_gap_is_not_an_ingest_gap

#### Scenario: a model whose capture states the figure is an ingest gap

- **Given** a store model with no structured `context_tokens` and a captured snapshot that
  states `131072-token context` for it
- **When** the store is analysed
- **Then** the model is NOT listed as un-captured, and the dimension's ingest set names it
- **Test:** tests/test_data_gap_analysis.py::test_an_acquisition_gap_is_not_an_ingest_gap

#### Scenario: the real store's split is a partition of the missing set

- **Given** the repository's own store and raw snapshots
- **When** the analysis runs
- **Then** for every dimension the acquisition set and the ingest set are disjoint and their
  union is exactly the missing set, and the signature is unchanged by the split
- **Test:** tests/test_data_gap_analysis.py::test_the_real_store_splits_every_missing_dimension

#### Scenario: the report and the filed issue say which gap it is

- **Given** a report with an acquisition gap
- **When** the report is rendered, and when an issue is filed from it
- **Then** both say “not stated by any captured post” for that dimension, and the ingest
  count is reported beside it
- **Test:** tests/test_data_gap_analysis.py::test_the_report_and_issue_body_name_an_acquisition_gap
