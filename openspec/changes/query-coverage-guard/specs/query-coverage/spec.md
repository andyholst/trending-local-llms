# query-coverage

## ADDED Requirements

### Requirement: A trending model is named by at least one search query

The refresh's query set MUST name every trending model, so the searches chase the models
the ranking is built from and not only the hardware keywords. The set is the curated
`SEARCH_GROUPS` **plus** a query derived from each trending model (its own id), and the
rule "does this query name this model" has exactly ONE implementation — in
`scripts/update_trending.py`, read by both the search prompts and the guard (rule 6d).
A model named by no query MUST make the coverage run exit non-zero, so a gap is loud and
distinguishable from a query that ran and found nothing.

WHEN the coverage run reads the store,
THEN every trending model is named by at least one query, or the run exits 1 and names
the models no query reaches.

#### Scenario: the top model is named by a derived query

- **Given** a store whose trending models include `qwen3.8-flash-next-125b`
- **When** the derived query set is built
- **Then** a query naming `qwen3.8-flash-next-125b` is in the set, and the coverage run exits 0
- **Test:** `tests/test_query_coverage.py::test_a_trending_model_gets_a_query_naming_it`

#### Scenario: a trending model no query names is a loud failure

- **Given** a store with a trending model whose id appears in no query
- **When** the coverage run evaluates it
- **Then** it exits 1 and the report names that model, so the gap is separable from a query that found nothing
- **Test:** `tests/test_query_coverage.py::test_an_uncovered_trending_model_fails_the_run`

#### Scenario: the curated base is kept, never replaced

- **Given** the hand-curated `SEARCH_GROUPS`
- **When** the derived model queries are appended
- **Then** every curated query is still present in the set the searches use
- **Test:** `tests/test_query_coverage.py::test_the_curated_queries_are_kept`

#### Scenario: the search prompts ask for the ranked models

- **Given** the four `_search-<backend>` prompts and the `query-coverage` target
- **When** the Makefile is read
- **Then** each prompt appends `$(MODEL_QUERIES)` and `_validate-search` runs `make query-coverage`
- **Test:** `tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired`

#### Scenario: a model is named only by its own id

- **Given** the query `qwen3.8-27b dflash speculative tokens`
- **When** it is checked against `qwen3.8-flash-next-125b`
- **Then** it does NOT name it — naming a sibling model must never cover it
- **Test:** `tests/test_query_coverage.py::test_a_sibling_model_query_does_not_cover`
