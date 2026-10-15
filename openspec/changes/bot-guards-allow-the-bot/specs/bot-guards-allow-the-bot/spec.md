# bot-guards-allow-the-bot

## ADDED Requirements

### Requirement: every bot guard admits the owner, a write+ collaborator, and the bot itself

Every bot pipeline's trigger guard SHALL allow BOTH `github.actor` and
`github.triggering_actor` to be the repo owner, a collaborator with
`write`/`maintain`/`admin`, or `github-actions[bot]` (the bot itself, i.e. a bot-to-bot
dispatch made with the default token), and SHALL refuse everything else — a read/triage
collaborator, a non-collaborator, or an API error.

#### Scenario: the bot itself may start a bot

- **GIVEN** the bot workflows `.github/workflows/{refresh-bot,fix-bot,issue-bot,issue-review-bot,publish-agent-image}.yml`,
- **WHEN** the trigger guard is run with `github.actor = github.triggering_actor = github-actions[bot]` on a `workflow_dispatch`,
- **THEN** it SHALL exit 0 (allowed).

- **Test:** `tests/test_workflows.py::test_guard_behaviour`

#### Scenario: a read/triage collaborator is still refused

- **GIVEN** a collaborator whose permission is `read` or `triage`,
- **WHEN** the trigger guard is run,
- **THEN** it SHALL exit non-zero (refused), as before.

- **Test:** `tests/test_workflows.py::test_guard_behaviour`

### Requirement: every bot guard with a cron carries the schedule bypass

Every bot pipeline that declares an `on.schedule` SHALL carry the
`if [ "$EVENT" = "schedule" ]` bypass in its guard, so a scheduled run is allowed
uniformly and does not depend on which identity GitHub attributes the cron run to.

#### Scenario: issue-bot's cron does not depend on the actor

- **GIVEN** `issue-bot.yml` and `issue-review-bot.yml`, both with an hourly cron,
- **WHEN** their guard scripts are read,
- **THEN** each SHALL contain the schedule bypass.

- **Test:** `tests/test_workflows.py::test_every_bot_guard_with_a_cron_has_the_schedule_bypass`
