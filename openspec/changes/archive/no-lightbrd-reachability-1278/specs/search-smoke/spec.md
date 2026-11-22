## ADDED Requirements

### Requirement: No live lightbrd reachability probe in CI

The pipelines SHALL NOT probe lightbrd.com for reachability. `_search-smoke` SHALL run `tests/test_smoke_search.py` offline, and `scripts/smoke_search.py` SHALL be manual-only.

#### Scenario: Pipeline wiring
- **WHEN** any workflow runs a search smoke step
- **THEN** it runs the offline test module and makes no network probe

### Requirement: A proven outage is not blocked, a half-answering mirror is

A leg with at least one target-error `OUTAGE` and zero `OK`/`FAIL` outcomes SHALL be excused. A leg with at least one `OK` alongside outages SHALL be red.

#### Scenario: Proven outage
- **WHEN** 4 outages and 7 timeouts, no OK and no FAIL
- **THEN** exit 0 with `PROVEN outage`

#### Scenario: Half-answering mirror
- **WHEN** one OK and ten outages
- **THEN** exit 2 with `HALF-answering`
