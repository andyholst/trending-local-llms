## ADDED Requirements

### Requirement: The prompt derivation never returns a query that names no model

`prompt_queries(store)` SHALL emit only queries that name at least one row of the
store, decided through the ONE predicate `update_trending.query_names_model`. A
query built from a row with no usable `id` names no model and SHALL NOT be emitted,
so a store whose ranked rows are all unnamed yields an EMPTY derivation rather than a
non-empty set of vacuous queries. The wiring assertion SHALL require both a
non-empty set and at least one query naming a real row.

#### Scenario: An all-nameless ranked store emits no query

- **Given** a store whose only ranked rows have an empty `id` (one trending, one aged)
- **When** `prompt_queries(store)` builds the derived set
- **Then** the unfiltered composition is non-empty yet names no model (the measured defect), and the seam emits no query at all
- **Test:** tests/test_query_coverage.py::test_an_all_nameless_store_yields_no_vacuous_query

#### Scenario: The wiring assertion cannot pass while naming nothing

- **Given** the repository's real store and the `_search-amd` recipe
- **When** the recipe is expanded with `make -n _search-amd`
- **Then** the live derivation is non-empty, at least one returned query names a real row, and every returned query appears in the expansion
- **Test:** tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired

#### Scenario: A named aged-out store still yields a non-empty derivation

- **Given** a store whose only model has a `last_seen` older than `TRENDING_WINDOW_DAYS`
- **When** `prompt_queries(store)` builds the derived set
- **Then** the set is non-empty and both halves name that model
- **Test:** tests/test_query_coverage.py::test_the_prompt_derivation_survives_an_aged_out_trending_band

#### Scenario: The coverage guard still refuses to be silenced

- **Given** the `--top 0` argument, or a trending model with no usable id
- **When** `scripts/query_coverage.py` runs
- **Then** `--top 0` exits 2, and the unnamed trending model exits 1 and names the gap
- **Test:** tests/test_query_coverage.py::test_a_silenced_guard_is_refused
