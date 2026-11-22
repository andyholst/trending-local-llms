## ADDED Requirements

### Requirement: Dual-source wake-up

The cron monitor SHALL emit ONLY stable `C:<comment id>` and
`R:<run id>:<status>:<conclusion>` keys, sorted, so the scheduler hash changes when
either a new comment appears or a CI run changes state. It SHALL NOT write to GitHub,
dispatch CI, grant access, or advance a cursor.

#### Scenario: A pipeline state changes but no comment is posted

- **WHEN** a workflow run goes from in_progress to completed/failure
- **THEN** the `R:` key changes and the agent wakes
- **AND** the agent posts a failure report on the owning issue before any fix

#### Scenario: Both machines watch the same repo

- **WHEN** asimov@mac and asimov@omarchy each run their own watcher
- **THEN** both wake on comments and CI state changes
- **AND** neither touches the other's claimed branch
