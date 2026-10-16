# outage-verdict-tolerates-a-failed-query

## MODIFIED Requirements

### Requirement: the live check's verdict names the failure, and only an outage is non-blocking

`gather_x` SHALL record this run's fetch outcomes (`queries`, `with_hits`,
`outage`, `refused`, `failed`, plus the outage statuses and reasons), and the
`--fetch --require-hits` verdict SHALL be derived from them rather than from the
hit count alone. The verdict SHALL be exactly one of:

* `refused` — Firecrawl returned no page for at least one query: OUR
  configuration, loud, exit non-zero. It SHALL be decided FIRST, so a refusal
  always wins over an outage.
* `outage` — the TARGET's own error page is what every query we could CLASSIFY
  got: `outage > 0`, `refused == 0`, `with_hits == 0`, and no query returned a
  real page (`queries - outage - refused - failed == 0`). Reported LOUDLY
  (`[outage] … the mirror is DOWN`) and DOES NOT FAIL: `live-smoke` gates
  qa-validate's `auto-merge`, so one down mirror used to red every open PR at once
  (issue #291). The message SHALL name any query that failed for another reason,
  and SHALL say it is not blocking.
* `quiet` — the mirror answered with no upstream error and no model was found:
  loud, exit non-zero, and the message SHALL point at the query set.

A query that FAILED at the transport level (a `failed` outcome — e.g.
`Connection refused`) SHALL NOT disqualify the outage: it proves nothing about the
mirror either way, so one of them MUST NOT flip a proven outage back to `quiet`
and re-block every open PR (issue #296). A PARTIAL outage where a query actually
ANSWERED a real page SHALL stay `quiet` (blocking), so a half-answering mirror
cannot slip a regression through as infrastructure noise. A run where NO query
proved an outage SHALL NOT be excused. The run SHALL also print the outcome
counts, so a `0 model hits` run is diagnosable (issue #293).

#### Scenario: a down mirror does not block every PR

- **GIVEN** a Firecrawl endpoint that answers every query with the mirror's own `502` error page,
- **WHEN** `scripts/update_trending.py --fetch --require-hits --dry-run` runs,
- **THEN** it SHALL exit `0`, print `[outage]` lines naming the mirror as DOWN, and NOT print the old `0 model hits` diagnosis.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_live_check_exits_zero_on_an_outage_and_non_zero_otherwise`

#### Scenario: one unclassifiable query does not unmask a proven outage

- **GIVEN** the outcomes of run `38862487215` — `queries=24`, `with_hits=0`, `outage=23` (the mirror's own `502`), `refused=0`, `failed=1` (a `Connection refused`),
- **WHEN** the verdict is computed,
- **THEN** it SHALL be `outage` with exit `0`, the lines SHALL name the mirror as DOWN and SHALL NOT say `QUIET SEARCH`, and the one transport-failed query SHALL be reported rather than hidden.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_transport_failed_query_does_not_unmask_a_proven_outage`

#### Scenario: a failure that proves no outage is never excused

- **GIVEN** `queries=24`, `outage=0`, `refused=0`, `failed=24` (every query a transport error),
- **WHEN** the verdict is computed,
- **THEN** it SHALL NOT be `outage` and it SHALL exit non-zero.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_transport_failed_query_does_not_unmask_a_proven_outage`

#### Scenario: a mirror that answered still blocks, even beside a failure

- **GIVEN** `queries=24`, `outage=10`, `refused=0`, `failed=1` — 13 queries returned a real page,
- **WHEN** the verdict is computed,
- **THEN** it SHALL be `quiet` with exit non-zero.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_transport_failed_query_does_not_unmask_a_proven_outage`

#### Scenario: a refusal wins over an outage

- **GIVEN** `queries=24`, `outage=20`, `refused=1` (Firecrawl refused),
- **WHEN** the verdict is computed,
- **THEN** it SHALL be `refused` with exit non-zero.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_transport_failed_query_does_not_unmask_a_proven_outage`

#### Scenario: a refusal and a quiet search still fail

- **GIVEN** a Firecrawl endpoint that refuses every scrape with `success: false`,
- **WHEN** the same command runs,
- **THEN** it SHALL exit non-zero and name the refusal; and

- **GIVEN** a reachable mirror answering `200` with no model in the page,
- **WHEN** the same command runs,
- **THEN** it SHALL exit non-zero and say `QUIET SEARCH`.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_live_check_exits_zero_on_an_outage_and_non_zero_otherwise`

#### Scenario: a partial outage with an answering mirror is still a failure

- **GIVEN** a run where some queries answered the target's error page and the rest answered with no model,
- **WHEN** the verdict is computed,
- **THEN** it SHALL be `quiet` with a non-zero exit code.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search`

#### Scenario: the outcome counts are printed

- **GIVEN** a run against any endpoint,
- **WHEN** the live check fetches,
- **THEN** it SHALL print `fetch outcomes: queries=… with-hits=… outage=… refused=… failed=…`.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search`
