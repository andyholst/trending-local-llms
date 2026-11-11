# search-queries Specification

## Purpose
TBD - created by archiving change ranked-gaps-ask-every-dimension. Update Purpose after archive.

## Requirements

### Requirement: Every ranked gap dimension is asked by a search query

Every dimension the data-gap analysis ranks (`data_gap_analysis.DIMENSIONS`)
MUST be asked by the derived footprint query of every top-N ranked model. The
dimension list has ONE implementation (rule 6d); the footprint suffix is pinned
to it by `DIMENSION_ASK_TOKENS`, and a dimension the analysis ranks that no
query asks MUST make `make query-coverage` fail loudly, naming the dimension —
"a search that never asked cannot be blamed for not finding" is only a real
distinction when the ask is proven.

#### Scenario: the suffix is pinned to the ranked dimensions

- **Given** `data_gap_analysis.DIMENSIONS` ranks `weight_gb`, `context_tokens`,
  `system_ram_min`, `storage_offload` and `engine_min_version`
- **When** `dimensions_not_asked()` compares them against `MODEL_FOOTPRINT_SUFFIX`
- **Then** it returns empty, and every ranked model's footprint query contains
  the token each dimension is asked by (`weights`, `context`, `ram`, `offload`,
  `version`)
- **Test:** tests/test_query_coverage.py::test_every_ranked_gap_dimension_is_asked

#### Scenario: an unasked ranked dimension fails the coverage guard

- **Given** a ranked dimension with no ask token in the footprint suffix
- **When** the coverage guard compares the ONE dimension list against the suffix
- **Then** `dimensions_not_asked()` names it and the guard exits 1 rather than
  reporting the model coverage as sufficient
- **Test:** tests/test_query_coverage.py::test_every_ranked_gap_dimension_is_asked

#### Scenario: the search contract names all five footprint asks

- **Given** the four search legs preload the `data-search` skill (rule 6p)
- **When** the skill's footprint line is read
- **Then** it names `vram ram context weights offload engine version` — the same
  suffix the derived queries carry — so a leg can capture `storage_offload` and
  `engine_min_version` into their optional measurement keys
- **Test:** tests/test_query_coverage.py::test_the_rule_is_documented
