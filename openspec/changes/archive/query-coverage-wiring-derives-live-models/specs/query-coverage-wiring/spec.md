# Query-coverage wiring derives the live model set

## ADDED Requirements

### Requirement: the wiring checks derive their expectation from the live store

`tests/test_query_coverage.py`'s wiring half MUST derive the expected model query from the
same store the coverage guard reads (`update_trending.derived_queries` /
`footprint_queries` over the real `data/models.json`), never from a pinned model id: the
top-N trend band is data that re-ranks with every weekly refresh, and a pinned literal reds
the whole suite — and auto-merge repo-wide — on the refresh that moves it (issue #1077). The
check is never vacuous: it also asserts the live derivation names at least one ranked model.

#### Scenario: a re-ranked trend band keeps the suite green

- **Given** the shipped store after a weekly refresh re-ranks the top-N band
  (measured: keeper merge `bfcff45` pushed the literal-pinned suite red on runs
  43775050919 and 43777818475)
- **When** `tests/test_query_coverage.py` runs over the current store
- **Then** the wiring checks pass by comparing the expanded `make -n _search-amd`
  prompt against `derived_queries(REAL_STORE)[0]` and `footprint_queries(REAL_STORE)[0]`
- **Test:** tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired

#### Scenario: a ranked model missing from the expanded prompt still goes red

- **Given** the expanded `_search-amd` prompt lacks the first derived query of the real
  store (the wiring broke)
- **When** the wiring checks run
- **Then** the check fails on `live_top[0] in out` — the rule "every ranked model reaches
  every leg" stays locked without any model id being pinned
- **Test:** tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired

#### Scenario: the derivation itself stays guarded

- **Given** a synthetic store whose trending model is named by no query
- **When** the coverage guard runs over it (`query_coverage.py`)
- **Then** it exits 1 naming the gap — the anti-tautology half that keeps deriving the
  wiring expectation from the derivation honest
- **Test:** tests/test_query_coverage.py::test_an_uncovered_trending_model_fails_the_run
