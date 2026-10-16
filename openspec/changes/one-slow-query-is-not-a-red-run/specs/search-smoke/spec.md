# search-smoke

## ADDED Requirements

### Requirement: a leg fails only on a majority of its queries missing the budget

The reachability probe SHALL decide each leg on its own, and a leg SHALL block the run ONLY when a
MAJORITY of its queries miss the budget. A minority missing SHALL NOT red the run; an unreachable
mirror (every query missing) SHALL still fail loudly.

#### Scenario: one slow query of four does not block the leg

- **GIVEN** a leg of four queries with one that missed the budget
- **WHEN** `leg_verdict(total=4, missed=1)` is asked
- **THEN** it is not blocking, and its note names the ratio and that the rest answered

- **Test:** `tests/test_smoke_search.py::test_one_slow_query_does_not_red_a_leg`

#### Scenario: a majority missing still blocks

- **GIVEN** legs where 4/4, 3/4, 2/3, 3/5 or 1/1 queries missed the budget
- **WHEN** `leg_verdict` is asked
- **THEN** every one of them IS blocking, so an unreachable source is never excused as a flake

- **Test:** `tests/test_smoke_search.py::test_one_slow_query_does_not_red_a_leg`

#### Scenario: a clean leg is silent and an exact half is not a majority

- **GIVEN** a leg with no misses, and a leg with exactly half missing
- **WHEN** `leg_verdict` is asked
- **THEN** the clean leg returns no note at all, and the exact half does not block

- **Test:** `tests/test_smoke_search.py::test_one_slow_query_does_not_red_a_leg`

### Requirement: the run summary distinguishes a flake from a dead source

The probe's run SHALL make the distinction visible in its own output: a leg that only sampled
slower than the budget SHALL say so in the summary and exit 0, and a leg that missed on a majority
SHALL exit non-zero saying the source is unreachable — and a leg that sampled slow SHALL NOT be
reported as "all backends returned HTTP 200".

#### Scenario: a flaky leg exits 0 and says it sampled

- **GIVEN** a leg of four queries with one slow one, driven through the probe seam
- **WHEN** the probe runs
- **THEN** it exits 0, the summary contains `SAMPLED` and the ratio, and it does not print "all
  backends returned HTTP 200"

- **Test:** `tests/test_smoke_search.py::test_the_run_summary_distinguishes_a_flake_from_a_dead_source`

#### Scenario: a dead source still exits non-zero

- **GIVEN** a leg whose queries all miss the budget
- **WHEN** the probe runs
- **THEN** it exits 2 and says a MAJORITY missed, that it is not a flake

- **Test:** `tests/test_smoke_search.py::test_the_run_summary_distinguishes_a_flake_from_a_dead_source`
