## ADDED Requirements

### Requirement: The real-store untraceable guard is order-insensitive

The real-store guard for `untraceable:context_tokens` SHALL assert exact membership
without depending on catalog order, so a refresh that reorders `models[]` does not
turn a correct classifier red. The `unstructured` / `untraceable` class boundary,
the disjoint partition of `missing`, and the absence of `untraceable:*` from the
issue-triggering signature SHALL be unchanged.

#### Scenario: A reordered catalog still reports the same untraceable ids

- **Given** the refreshed 120-model store in which `qwen-3.6-27b` precedes `gemma-4-12b`
- **When** `analyse()` classifies context figures stated in prose with no captured post behind them
- **Then** `untraceable:context_tokens` contains exactly those two models regardless of order and `unstructured:context_tokens` is empty
- **Test:** `tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at`

#### Scenario: A captured-post figure stays an ingest job

- **Given** a model whose own prose states a window AND whose captured post states that window
- **When** the store is analysed
- **Then** it is in `unstructured:context_tokens` and NOT in `untraceable:context_tokens`
- **Test:** `tests/test_data_gap_analysis.py::test_a_stated_figure_no_post_supports_is_its_own_class`

#### Scenario: The four buckets remain a disjoint partition

- **Given** the four buckets `not_captured` / `unstructured` / `captured_prose` / `untraceable`
- **When** a stated figure is classified
- **Then** they remain a disjoint partition of `missing` and no `untraceable:*` entry enters the issue-triggering signature
- **Test:** `tests/test_data_gap_analysis.py::test_the_real_store_splits_every_missing_dimension`

#### Scenario: The full real-store suite is green on the regenerated store

- **Given** the full real-store suite on the regenerated store
- **When** `python3 tests/test_data_gap_analysis.py` runs
- **Then** it reports `PASSED 332 | FAILED 0` with no order-dependent failure
- **Test:** `tests/test_data_gap_analysis.py::main` (module run)
