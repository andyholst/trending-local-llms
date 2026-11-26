# hermes-pin-freshness

## ADDED Requirements

### Requirement: The CI recorder has a token for its public channel read

The `refresh-bot` job that runs `make hermes-pin-channel-record` SHALL provide `GH_TOKEN` from
`${{ github.token }}`. The default token is sufficient for the public
`gh api repos/NousResearch/hermes-agent/releases/latest` read; the owner PAT SHALL NOT be used
for that read (AGENTS.md rule 6b). A job block with no token SHALL be refused by the wiring guard.

#### Scenario: the aggregate job can record the channel payload

- **Given** the checked-out `refresh-bot.yml` aggregate job that runs the recorder through the
  Makefile seam
- **When** `test_the_aggregate_job_gives_the_pin_recorder_a_token` inspects that job block
- **Then** the block contains `GH_TOKEN: ${{ github.token }}`, does not contain the owner PAT, and
  the guard fails on the previous tokenless workflow
- **Test:** tests/test_hermes_pin_freshness.py::test_the_aggregate_job_gives_the_pin_recorder_a_token
