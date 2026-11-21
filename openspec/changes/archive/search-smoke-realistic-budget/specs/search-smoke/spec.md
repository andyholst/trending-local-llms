## ADDED Requirements

### Requirement: The reachability probe budget is owned once and is realistic

The Makefile SHALL own a single `SEARCH_SMOKE_BUDGET` variable (default 90s). The
`_search-smoke` recipe SHALL pass that value to `scripts/smoke_search.py`, and
the public `search-smoke` recipe SHALL forward it into the container. Both
`.github/workflows/qa-validate.yml` and `.github/workflows/refresh-bot.yml`
SHALL pass the budget explicitly to their `make` call and SHALL name the new
budget in their step titles. The budget SHALL be at least 30s, because a shorter
one measures the client alarm and times out before any successful scrape.

#### Scenario: The pipeline probe measures the source, not the client alarm

- **Given** the Makefile and both workflow files at the change's head
- **When** `tests/test_smoke_search.py::test_ci_search_smoke_budget_is_realistic` reads them
- **Then** it finds the Makefile pin (>= 30s), the recipe using it, the forwarded value, and explicit `SEARCH_SMOKE_BUDGET=90` in both pipelines, with no `within 3s` step title
- **Test:** tests/test_smoke_search.py::test_ci_search_smoke_budget_is_realistic

#### Scenario: The guard is red on the hardcoded 3s code

- **Given** `origin/master`'s Makefile and workflows with `--budget 3` and the `within 3s` step titles
- **When** the same test is run against those files
- **Then** it fails, naming the missing Makefile pin
- **Test:** tests/test_smoke_search.py::test_ci_search_smoke_budget_is_realistic

### Requirement: A genuinely dead source still fails the gate

Raising the budget SHALL NOT change the verdict rules: a leg whose majority of
queries miss the budget still blocks, and an upstream 5xx error page remains a
non-blocking `OUTAGE` labelled loudly. A real outage therefore still misses
every query at the new budget and reds the run; it is never excused as a flake.

#### Scenario: The majority rule is untouched

- **Given** four queries of one leg that all time out at the (larger) budget
- **When** `leg_verdict(4, 4)` is evaluated
- **Then** it returns `(True, "4/4 queries did not answer within the budget")`
- **Test:** tests/test_smoke_search.py::test_the_run_summary_distinguishes_a_flake_from_a_dead_source
