# firecrawl-refusal-is-loud

## ADDED Requirements

### Requirement: a refused Firecrawl scrape raises, and quotes the refusal

`fetch_via_firecrawl` SHALL return the scraped page ONLY when Firecrawl actually
returned one. A refusal (`HTTP 200` with `{"success": false, "error": …}`), a
response carrying neither `markdown` nor `html`, a non-JSON body, or JSON that is
not a scrape result SHALL raise `FirecrawlRefusal`, and the error SHALL quote
Firecrawl's own reason. A refusal MUST NOT be returned as a page: doing so makes
every query look like a search that ran and found nothing (`0 model hits`), which
is the wrong diagnosis and is indistinguishable from a genuinely quiet search.

#### Scenario: a refusal is not a page

- **GIVEN** a Firecrawl endpoint that answers `200` with `{"success": false, "error": "Payment Required: no credits remaining"}`,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** it SHALL raise, the message SHALL contain Firecrawl's reason, and it SHALL NOT return a page.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_refused_scrape_raises_and_quotes_firecrawl`

#### Scenario: a success with no page is still not a page

- **GIVEN** a Firecrawl endpoint that answers `200` with `{"success": true, "data": {}}`,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** it SHALL raise.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_200_without_a_page_raises`

#### Scenario: a non-JSON body is not a page

- **GIVEN** a Firecrawl endpoint that answers `200` with an HTML error page,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** it SHALL raise and say what came back.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_non_json_body_raises`

### Requirement: a page the TARGET served as an error is an UPSTREAM outage, not a page

Firecrawl answers `HTTP 200` of its own and reports the fetched page's real status
in `data.metadata.statusCode`, so a DOWN MIRROR arrives as a *successful scrape of
an error page*. `fetch_via_firecrawl` SHALL raise `UpstreamOutage` — a class
distinct from `FirecrawlRefusal` — when the page it received is the target's own
error page: `data.metadata.statusCode >= 500`, or Cloudflare's error page
(`Error code 5NN` / a `5xx-error-landing` link). It SHALL name the status the
target answered. A `4xx` page (a bot wall) SHALL stay a `FirecrawlRefusal`, and a
healthy page SHALL be returned unchanged, so the guard can never excuse our own
failure as infrastructure, nor eat a real page.

#### Scenario: the mirror's 502 is not a page of posts

- **GIVEN** a Firecrawl endpoint that answers `200` with `{"success": true, "data": {"markdown": "# Bad gatewayError code 502 …", "metadata": {"statusCode": 502}}}`,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** it SHALL raise `UpstreamOutage` naming the `502`, not return the page.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_mirror_error_page_is_an_upstream_outage_not_a_page`

#### Scenario: an error page without a reported status is still an outage

- **GIVEN** a `200` whose page is Cloudflare's `Error code 504` and which reports no upstream status,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** it SHALL raise `UpstreamOutage`.

- **Test:** `tests/test_firecrawl_fetch.py::test_an_error_page_without_a_reported_status_is_still_an_outage`

#### Scenario: a bot wall is OURS, not the mirror's

- **GIVEN** a `200` whose page is a Cloudflare challenge and whose `metadata.statusCode` is `403`,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** it SHALL raise `FirecrawlRefusal`, so the check keeps failing.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_bot_wall_is_a_refusal_not_an_outage`

#### Scenario: a healthy page is returned untouched

- **GIVEN** a `200` with `metadata.statusCode: 200` and a post page,
- **WHEN** `fetch_via_firecrawl` runs against it,
- **THEN** the page SHALL be returned verbatim.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_healthy_page_is_never_read_as_an_outage`

### Requirement: the live check's verdict names the failure, and only an outage is non-blocking

`gather_x` SHALL record this run's fetch outcomes (`queries`, `with_hits`,
`outage`, `refused`, `failed`, plus the outage statuses and reasons), and the
`--fetch --require-hits` verdict SHALL be derived from them rather than from the
hit count alone. The verdict SHALL be exactly one of:

* `outage` — EVERY query came back as the target's own error page. Reported
  LOUDLY (`[outage] … the mirror is DOWN`) and DOES NOT FAIL: `live-smoke` gates
  qa-validate's `auto-merge`, so one down mirror used to red every open PR at once
  (issue #291).
* `refused` — Firecrawl returned no page for at least one query: OUR
  configuration, loud, exit non-zero.
* `quiet` — the mirror answered with no upstream error and no model was found:
  loud, exit non-zero, and the message SHALL point at the query set.

A PARTIAL outage SHALL stay `quiet` (blocking): an outage is only excused when
EVERY query is one, so a half-answering mirror cannot slip a regression through as
infrastructure noise. The run SHALL also print the outcome counts, so a `0 model
hits` run is diagnosable (issue #293).

#### Scenario: a down mirror does not block every PR

- **GIVEN** a Firecrawl endpoint that answers every query with the mirror's own `502` error page,
- **WHEN** `scripts/update_trending.py --fetch --require-hits --dry-run` runs,
- **THEN** it SHALL exit `0`, print `[outage]` lines naming the mirror as DOWN, and NOT print the old `0 model hits` diagnosis.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_live_check_exits_zero_on_an_outage_and_non_zero_otherwise`

#### Scenario: a refusal and a quiet search still fail

- **GIVEN** a Firecrawl endpoint that refuses every scrape with `success: false`,
- **WHEN** the same command runs,
- **THEN** it SHALL exit non-zero and name the refusal; and

- **GIVEN** a reachable mirror answering `200` with no model in the page,
- **WHEN** the same command runs,
- **THEN** it SHALL exit non-zero and say `QUIET SEARCH`.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_live_check_exits_zero_on_an_outage_and_non_zero_otherwise`

#### Scenario: the outcome counts are printed

- **GIVEN** a run against any endpoint,
- **WHEN** the live check fetches,
- **THEN** it SHALL print `fetch outcomes: queries=… with-hits=… outage=… refused=… failed=…`.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search`

#### Scenario: a partial outage is still a failure

- **GIVEN** a run where some queries answered the target's error page and the rest answered with no model,
- **WHEN** the verdict is computed,
- **THEN** it SHALL be `quiet` with a non-zero exit code.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_verdict_tells_an_outage_from_a_refusal_and_a_quiet_search`

### Requirement: the reachability smoke calls a down mirror an OUTAGE

`probe` SHALL carry the upstream status Firecrawl reports and SHALL label an
upstream `>= 500` page `OUTAGE`: reported loudly, NOT retried (retrying a down
mirror is noise) and NOT a smoke failure, so a down mirror is visible without
blocking every PR. A `4xx` upstream page SHALL be a `FAIL`, so a bot wall is never
excused.

#### Scenario: a 502 upstream is its own label

- **GIVEN** a scrape result of `status=200, success=true, upstream=502`,
- **WHEN** `probe` runs,
- **THEN** the label SHALL be `OUTAGE`, the upstream status SHALL be carried through, and exactly ONE request SHALL be made.

- **Test:** `tests/test_smoke_search.py::test_an_upstream_error_page_is_its_own_outage_label`

#### Scenario: a healthy scrape and a bot wall are unchanged

- **GIVEN** a scrape result with `upstream=200`,
- **WHEN** `probe` runs,
- **THEN** the label SHALL be `OK`; and

- **GIVEN** `upstream=403`,
- **THEN** the label SHALL be `FAIL`.

- **Test:** `tests/test_smoke_search.py::test_an_upstream_error_page_is_its_own_outage_label`

### Requirement: a successful scrape returns the page, having built the right request

`fetch_via_firecrawl` SHALL POST to Firecrawl's scrape endpoint with the API key
in the `Authorization` header, `formats: ["markdown"]` (what the parser reads)
and the lightbrd URL it was given, and SHALL return `data.markdown`.

#### Scenario: the request we build is the request the API sees

- **GIVEN** a local server standing in for Firecrawl,
- **WHEN** `fetch_via_firecrawl` scrapes a lightbrd search URL,
- **THEN** the server SHALL observe exactly one POST to `/v1/scrape`, bearing
  the `Authorization` header, `formats: ["markdown"]` and that URL, and the
  markdown SHALL be returned.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_successful_scrape_returns_the_page_and_builds_the_right_request`

### Requirement: a failed fetch is loud, and the endpoint seam is test-only

`gather_x` SHALL warn per query whose fetch failed, so a failed fetch is
separable from a search that ran and found nothing; and the offline endpoint seam
SHALL default to Firecrawl's real `https://api.firecrawl.dev/v1/scrape`
(an empty override does not blank it), so the seam can only ever narrow a test,
never production.

#### Scenario: a failed fetch warns instead of reporting a quiet search

- **GIVEN** a Firecrawl endpoint that refuses every scrape,
- **WHEN** `gather_x` runs over the search groups,
- **THEN** it SHALL return no model hits, SHALL warn at least once per backend,
  and the warnings SHALL carry Firecrawl's reason.

- **Test:** `tests/test_firecrawl_fetch.py::test_a_refused_scrape_warns_per_query_instead_of_reporting_a_quiet_search`

#### Scenario: the seam defaults to Firecrawl

- **GIVEN** no `FIRECRAWL_SCRAPE_URL` (and an empty one),
- **WHEN** `firecrawl_scrape_url()` is read,
- **THEN** it SHALL be `https://api.firecrawl.dev/v1/scrape`.

- **Test:** `tests/test_firecrawl_fetch.py::test_the_endpoint_seam_defaults_to_firecrawl`
