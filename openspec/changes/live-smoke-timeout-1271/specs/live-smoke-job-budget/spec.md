## ADDED Requirements

### Requirement: The `live-smoke` job timeout covers its worst-case query set

The `live-smoke` job in `.github/workflows/qa-validate.yml` SHALL set
`timeout-minutes` to at least the worst-case probe time of its full query set:
the number of curated queries in `scripts/query_vocab.py` multiplied by the
Makefile's `SEARCH_SMOKE_BUDGET` and by the number of attempts the workflow runs
(`--retries 1` => 2), with margin. A guard SHALL fail when the timeout no longer
covers that product.

#### Scenario: The shipped timeout covers the whole curated query set

- **Given** the workflow's `live-smoke` job, the real query vocabulary and the Makefile's `SEARCH_SMOKE_BUDGET`
- **When** the guard reads the three and computes the worst-case probe time
- **Then** the job's `timeout-minutes` is at least that product and the guard passes
- **Test:** tests/test_smoke_search.py::test_ci_live_smoke_timeout_covers_the_worst_case_query_set

#### Scenario: A timeout below the worst case is refused

- **Given** a workflow text whose `live-smoke` `timeout-minutes` is 25
- **When** the guard computes the worst-case probe time of the real vocabulary
- **Then** the guard fails naming the timeout it read and the minimum it computed
- **Test:** tests/test_smoke_search.py::test_ci_live_smoke_timeout_covers_the_worst_case_query_set
