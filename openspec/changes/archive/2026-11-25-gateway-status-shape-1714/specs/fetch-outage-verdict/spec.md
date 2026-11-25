## ADDED Requirements

### Requirement: A gateway status needs an HTTP status shape

`is_upstream_timeout` SHALL recognise a gateway failure only when the status digits appear in an HTTP status SHAPE (for example `HTTP Error 502`, `HTTP 522`, `statusCode: 502`, `502 Bad Gateway`, `502 Server Error`), never from a bare digit sequence elsewhere in the reason text. Read-timeout wording and explicit gateway wording (`bad gateway`, `service unavailable`, `gateway error`) SHALL remain recognised. The measured run-45526182085 shape (`34 × read timeout + HTTP Error 502: Bad Gateway`) SHALL remain a recognised transport failure.

#### Scenario: Incidental status digits are not a transport failure

- **Given** a reason string `parsed 502 bytes from the page` (and the same shape with 503, 504, 522)
- **When** `is_upstream_timeout` classifies the exception
- **Then** it returns False
- **Test:** tests/test_firecrawl_fetch.py::test_a_gateway_code_needs_an_http_status_shape

#### Scenario: The measured gateway shape is still recognised

- **Given** the reason strings `HTTP Error 502: Bad Gateway`, `target answered HTTP 522`, `metadata statusCode: 502` and `upstream returned 502 Bad Gateway`
- **When** `is_upstream_timeout` classifies each exception
- **Then** it returns True for each
- **Test:** tests/test_firecrawl_fetch.py::test_a_gateway_code_needs_an_http_status_shape

### Requirement: An incidental gateway number keeps a quiet search blocking

`zero_hit_verdict` SHALL keep the `quiet`/exit-1 verdict for a run where every query failed and the only gateway-looking digits are incidental prose, because `gather_x` derives `timeouts` through `is_upstream_timeout`. `live-smoke` gates `auto-merge`, so a non-blocking outage verdict must never come from a false-positive classifier.

#### Scenario: All-failed run with only incidental gateway digits

- **Given** `queries=35, failed=35, with_hits=0, outage=0, refused=0` and every reason is `parsed 502 bytes from the page`
- **When** `zero_hit_verdict` classifies the run with `timeouts` derived through the real `is_upstream_timeout`
- **Then** the verdict is `quiet` with exit code 1
- **Test:** tests/test_firecrawl_fetch.py::test_a_gateway_code_needs_an_http_status_shape
