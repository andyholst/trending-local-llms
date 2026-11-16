# Query-coverage wiring derives the live model set

## Why

`tests/test_query_coverage.py::test_the_prompts_and_the_guard_are_wired` asserted that the
expanded `_search-amd` prompt contains the literal `qwen3.8-flash-next-125b …` queries — the
model that happened to top the trend band when the test was written. The trend band is data:
the weekly refresh keeper `bfcff45` re-ranked it and `make test` on `master` went red
(push runs 43775050919 `929ba1f` and 43777818475 `061ceaa`, `PASSED 79 | FAILED 2`), blocking
auto-merge repo-wide (rule 6q — a red push to master has no repairer).

## What Changes

The two live-store wiring checks derive their expected query from the store the guard itself
reads — `update_trending.derived_queries(REAL_STORE)[0]` and
`footprint_queries(REAL_STORE)[0]` — plus a non-vacuity check that the live derivation names
at least one ranked model. The synthetic-store tests (which lock derivation correctness and the
exit-1 guard) are untouched, so deriving the expectation from the same implementation is not
tautological: wiring regressions still go red through `$(MODEL_QUERIES)` presence checks, and
derivation regressions still go red through the planted stores.

## Impact

- `tests/test_query_coverage.py` (two wiring checks + one new non-vacuity check)
- Capability spec: `query-coverage-wiring`

## Not covered

- The prompt/keyword vocab itself, the search legs, and the coverage guard's exit-1 semantics —
  unchanged.
- Any change to `update_trending` derivation behavior — none needed; the fix is in the test.

**Issue:** #1077
PR: #1078
