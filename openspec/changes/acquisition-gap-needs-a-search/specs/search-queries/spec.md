# search-queries

## ADDED Requirements

### Requirement: A ranked model gets a footprint query

Every top-`QUERY_TOP_N` trending model MUST get a query that names it AND asks for its
memory footprint (`vram`, `ram`, `context`, `weights`) in addition to the throughput query,
and every search leg MUST carry both.

#### Scenario: the footprint query names the model and asks for its footprint

- **Given** a store whose trending band is `qwen3.8-flash-next-125b`
- **When** the footprint queries are derived
- **Then** one query names that model and carries `vram`, `ram`, `context` and `weights`
- **Test:** tests/test_query_coverage.py::test_a_footprint_query_names_each_ranked_model

#### Scenario: every search leg carries the footprint queries

- **Given** the four search legs and a trending model set
- **When** the query set each leg sends is built
- **Then** each leg carries the curated queries, the throughput query AND the footprint query
- **Test:** tests/test_query_coverage.py::test_a_footprint_query_names_each_ranked_model

#### Scenario: the prompts and the guard send the footprint queries

- **Given** the Makefile and the one query implementation
- **When** the derived queries are expanded for a search leg
- **Then** the expanded prompt carries a footprint query, and `--queries` prints exactly what
  the prompts append
- **Test:** tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired
