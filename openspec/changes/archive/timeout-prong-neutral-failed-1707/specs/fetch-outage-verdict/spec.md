## ADDED Requirements

### Requirement: A neutral failed query does not condemn a transport outage

`zero_hit_verdict` SHALL classify an all-transport-failure run (at least one recognised timeout or gateway failure, no answered query, no hit, no refusal) as `outage` with exit code 0, whether or not other queries were unclassifiable `failed` queries. Those neutral `failed` queries SHALL be reported in the verdict lines, never hidden. A partial failure — any answered query — SHALL remain `quiet` with exit code 1.

#### Scenario: Timeouts mixed with an unclassifiable failure

- **Given** `queries=35, failed=35, timeouts=34` (34 read timeouts plus one `Connection refused`), with no outage, refusal, hit or answered query
- **When** `zero_hit_verdict` classifies the run
- **Then** the verdict is `outage` with exit code 0, the lines name the unreachable mirror, and the neutral failure is reported
- **Test:** tests/test_firecrawl_fetch.py::test_a_timeout_mixed_with_a_neutral_failed_query_is_an_outage

#### Scenario: A partial timeout still blocks

- **Given** one timeout among otherwise answered queries (`queries=12, failed=1, timeouts=1`)
- **When** `zero_hit_verdict` classifies the run
- **Then** the verdict stays `quiet` with exit code 1
- **Test:** tests/test_firecrawl_fetch.py::test_a_partial_timeout_stays_red

### Requirement: Both outage prongs use one discriminator

The timeout prong and the error-page prong SHALL apply the same discriminator — `queries`, at least one recognised failure class, `not with_hits`, `not answered` — so the same unreachable-mirror shape gets the same verdict whichever way the transport failed. The timeout prong SHALL NOT carry an extra sum equality that the error-page prong lacks.

#### Scenario: Parity between the two outage prongs

- **Given** the source of `zero_hit_verdict`
- **When** the two outage-prong guards are compared
- **Then** neither prong contains a `+ outage == queries` sum-equality discriminator, and both check `not answered` and `not with_hits`
- **Test:** tests/test_firecrawl_fetch.py::test_the_timeout_and_error_page_prongs_share_a_discriminator
