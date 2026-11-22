## ADDED Requirements

### Requirement: Deterministic comment change detector

The monitor SHALL baseline the local cursor to the last 24h on first run, query the
newest 100 comments first, filter to those newer than the cursor, and print ONLY sorted
comment IDs (or `NONE`). It SHALL NOT ignore any author, including the agent's own
identity, and SHALL NOT advance the cursor.

#### Scenario: A test comment by the agent

- **WHEN** asimov-agent posts a new comment
- **THEN** its ID appears in the monitor output
- **AND** the next cron tick wakes the comment agent

#### Scenario: No new comments

- **WHEN** the comment set is unchanged
- **THEN** the monitor emits byte-identical output so the scheduler suppresses the agent
