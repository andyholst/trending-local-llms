# query-coverage-report Specification

## Purpose
TBD - created by archiving change query-coverage-report-named-queries. Update Purpose after archive.

## Requirements

### Requirement: The coverage report counts only queries that name a model

`report(store, top_n, aged_n)` SHALL compute its derived, footprint, aged-throughput and
aged-footprint counts and its `sent in total` line from the SAME filtered seam as
`--queries`: a composed query that names no row of the store SHALL NOT be counted, so
the report cannot claim a search leg sends a query no prompt carries. The report and
`--queries` SHALL agree on a store whose ranked rows include one with an empty `id`.

#### Scenario: The report agrees with `--queries` on a store with an unnamed ranked row

- **Given** a store with one named trending row and one ranked row whose `id` is empty
- **When** `report(store, top_n, aged_n)` renders and `prompt_queries(store, top_n, aged_n)` is built
- **Then** the reported per-category counts equal the filtered set sizes, and the reported `sent in total` equals `len(SEARCH_GROUPS) * (len(curated) + len(prompt_queries(...)))`
- **Test:** tests/test_query_coverage.py::test_the_report_counts_only_queries_that_name_a_row

#### Scenario: The shipped store's report is unchanged

- **Given** the repository's own store, where every ranked row has a usable `id`
- **When** the default report is rendered
- **Then** every count and the `sent in total` line are identical to the pre-change composition
- **Test:** tests/test_query_coverage.py::test_the_real_store_is_covered

#### Scenario: An all-nameless store emits nothing and the report says so

- **Given** a store whose only ranked rows have an empty `id`
- **When** `report(store, top_n, aged_n)` renders
- **Then** the derived/footprint/aged counts are zero and `sent in total` counts only the curated base
- **Test:** tests/test_query_coverage.py::test_the_report_counts_only_queries_that_name_a_row
