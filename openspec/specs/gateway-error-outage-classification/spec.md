# gateway-error-outage-classification Specification

## Purpose
TBD - created by archiving change gateway-error-outage-class. Update Purpose after archive.

## Requirements

### Requirement: A transport-level gateway error is a transport failure

`update_trending.is_upstream_timeout` SHALL recognise the gateway-error family of transport
failures — a `502`, a `503`, a `Bad Gateway` / `Service Unavailable` wording and a `gateway error`
— as the same unreachable-mirror class as a read timeout, so that one gateway error among otherwise
timed-out queries cannot break the total-outage arithmetic in `zero_hit_verdict`.

The widening is deliberately narrow: only exception TEXT from the fetch transport is inspected, and
only these tokens. A returned page, a Firecrawl refusal and an answered query are unaffected.

#### Scenario: A transport-level gateway error is counted as a timeout

- **Given** a fetch that raises `RuntimeError("HTTP Error 502: Bad Gateway")`, one that raises
  `RuntimeError("503 Server Error: Service Unavailable for url")`, and one that raises
  `RuntimeError("504 Gateway Time-out")`
- **When** `is_upstream_timeout` reads each exception
- **Then** each answers `True`, while `RuntimeError("connection refused")` still answers `False`
- **Test:** tests/test_firecrawl_fetch.py::test_timeout_family_recognises_gateway_and_read_timeouts

#### Scenario: One gateway error among timeouts is an outage, not a quiet search

- **Given** a run of 35 queries of which 34 raised a read timeout and one raised
  `HTTP Error 502: Bad Gateway` (no hits, no refusals, no answered query)
- **When** `zero_hit_verdict` classifies the stats
- **Then** the kind is `outage` and the exit code is `0` — the mirror is excused as unreachable
- **Test:** tests/test_firecrawl_fetch.py::test_a_single_gateway_error_among_timeouts_is_an_outage

#### Scenario: A genuinely answered query still reds

- **Given** the same 35-query run but with ONE query returning a real page (and no model hits)
- **When** `zero_hit_verdict` classifies the stats
- **Then** the kind is `quiet` and the exit code is `1` — a half-answering mirror is never excused
- **Test:** tests/test_firecrawl_fetch.py::test_a_single_gateway_error_among_timeouts_is_an_outage
