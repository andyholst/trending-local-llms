## ADDED Requirements

### Requirement: The prompt-wiring assertion does not depend on the engagement window

The wiring check SHALL derive its expected queries from the union of the TOP-N
trending pair and the QUERY_AGED_N aged pair through the ONE `prompt_queries()`
seam, and SHALL require that set to be non-empty and to reach the expanded prompt.
An empty top-N trending band — every `last_seen` older than `TRENDING_WINDOW_DAYS`,
the legitimate state between weekly refreshes — SHALL NOT be reported as a wiring
failure. The coverage guard's own decision SHALL remain unchanged: exit 1 when a
ranked model no query names, and refusal of `--top 0`.

#### Scenario: An aged-out store still yields a non-empty prompt derivation

- **Given** a store whose only model has a `last_seen` older than `TRENDING_WINDOW_DAYS`
- **When** `prompt_queries(store)` builds the derived set
- **Then** the set is non-empty, and both the throughput query and the footprint query name that model
- **Test:** tests/test_query_coverage.py::test_the_prompt_derivation_survives_an_aged_out_trending_band

#### Scenario: Every derived query reaches the expanded prompt

- **Given** the repository's real store and the `_search-amd` recipe
- **When** the recipe is expanded with `make -n _search-amd`
- **Then** every query `prompt_queries(REAL_STORE)` returns appears in the expansion, including a footprint query
- **Test:** tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired

#### Scenario: The coverage guard still refuses to be silenced

- **Given** the `--top 0` argument
- **When** `scripts/query_coverage.py` runs
- **Then** it exits 2 and says the top must be at least 1
- **Test:** tests/test_query_coverage.py::test_a_silenced_guard_is_refused

#### Scenario: A ranked model no query names is still a loud failure

- **Given** a trending model with no usable id
- **When** the coverage run evaluates it
- **Then** it exits 1 and names the gap
- **Test:** tests/test_query_coverage.py::test_an_uncovered_trending_model_fails_the_run
