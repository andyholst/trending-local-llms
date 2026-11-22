## ADDED Requirements

### Requirement: Offline Hermes call smoke

The system SHALL provide `make agent-hermes-smoke`, which FAILS when the Makefile and Dockerfile Hermes pins disagree, the CI installer is missing, the chain has no primary model or credential NAME, or the base_url is not https. It SHALL NOT make a network call or read a credential VALUE.

#### Scenario: Consistent image
- **WHEN** pins match and the chain carries a primary model, https endpoint and key_env name
- **THEN** the check prints `[agent-hermes-smoke] OK` and exits 0

#### Scenario: Pin drift
- **WHEN** the Dockerfile pin differs from the Makefile pin
- **THEN** the check names the drift and exits non-zero
