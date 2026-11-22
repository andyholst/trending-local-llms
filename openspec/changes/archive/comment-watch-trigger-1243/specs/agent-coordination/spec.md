## ADDED Requirements

### Requirement: Comment trigger

The agent SHALL run `make comment-watch` while waiting on CI or between work items.
For every comment newer than the local cursor it SHALL read the full thread, assess
it, reply on that thread, file an issue for any new work requested, and implement
that work in a worktree PR. It SHALL NOT mark a comment read before the thread was
read and answered.

#### Scenario: A new comment asks for a fix

- **WHEN** `make comment-watch` reports a new comment requesting a change
- **THEN** the agent reads the full thread and replies with its identity
- **AND** files an issue for the change and implements it in a PR with an OpenSpec change

#### Scenario: Cursor safety

- **WHEN** a late API page contains an older comment
- **THEN** the local cursor never moves backwards
- **AND** self-authored comments are never reported as new events

#### Scenario: Rule weakened

- **WHEN** rule 6w loses its full-thread reading, reply, filing or implementation duty
- **THEN** `tests/test_comment_watch.py` fails with a named finding
