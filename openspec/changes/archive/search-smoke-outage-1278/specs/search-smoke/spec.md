## ADDED Requirements

### Requirement: A proven outage is not pre-empted by the majority rule

The search smoke SHALL classify a leg whose probes contain at least one target-error `OUTAGE` and zero `OK`/`FAIL` outcomes as a non-blocking outage, even when the remaining queries timed out. A leg with any `OK` SHALL remain red, and an all-`TIMEOUT` leg with no `OUTAGE` SHALL remain red.

#### Scenario: Proven outage with timeouts
- **WHEN** 4 queries return the target's own error page and 7 time out
- **THEN** the run prints `PROVEN outage` and exits 0

#### Scenario: Outage plus a real answer
- **WHEN** at least one query answers normally
- **THEN** the run stays red

#### Scenario: All timeouts
- **WHEN** every query times out and none is an `OUTAGE`
- **THEN** the run stays red
