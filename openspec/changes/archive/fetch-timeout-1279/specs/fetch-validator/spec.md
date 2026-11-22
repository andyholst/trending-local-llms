## ADDED Requirements

### Requirement: A total upstream timeout is a non-blocking outage

The fetch validator SHALL bound each query with `--fetch-timeout` and SHALL classify a result where every query timed out or returned a gateway timeout, with no hits, no refusal and no answered page, as a named non-blocking outage. A PARTIAL timeout or a quiet search SHALL remain red.

#### Scenario: Mirror unreachable
- **WHEN** all 12 queries fail with `The read operation timed out`
- **THEN** the verdict is `outage`, exit 0, and the message says `UNREACHABLE`

#### Scenario: Mirror answers but is quiet
- **WHEN** only 1 of 12 queries times out and the rest answer normally with no hits
- **THEN** the verdict is `quiet` and exit 1
