# fleet-cadence

## REMOVED Requirements

### Requirement: every scheduled pipeline runs once a week on Wednesday

**Reason:** #1029 (owner directive 2026-11-15): only the data gatherer keeps a cron; every other pipeline is dispatch-only. The weekly semantics for the alarms that remain (the WEEK-wide windows) stay in force unchanged.

## ADDED Requirements

### Requirement: only the data gatherer keeps an on.schedule; the rest of the fleet is dispatch-only

`refresh-bot.yml` is the ONLY workflow in `.github/workflows/` with an `on.schedule` — the
weekly Wednesday data refresh (`0 6 * * 3` and the `43 17 * * 3` backup, unchanged). Every
other pipeline (`issue-bot`, `issue-review-bot`, `architecture-bot`, `bot-health`,
`code-review-bot`, `pr-health`, `queued-alarm`) is **dispatch-only**: no `schedule:` block,
and `issue-bot.yml` carries no `issues:` trigger either — starting a bot pipeline is an
owner/collaborator/bot dispatch admitted by that pipeline's `guard` (rule 6j).

#### Scenario: the gatherer is the only cron left

- **Given** every workflow under `.github/workflows/`
- **When** the suite scans their trigger surfaces
- **Then** exactly one workflow (`refresh-bot.yml`) declares `on.schedule` (its two weekly
  Wednesday slots), and every other workflow's triggers contain no `schedule:` block
- **Test:** tests/test_workflows.py::test_only_the_refresh_pipeline_carries_a_schedule

#### Scenario: no bot-authored issue can start an implementer

- **Given** `issue-bot.yml`'s trigger surface
- **When** the suite reads its `on:` block
- **Then** it contains only `workflow_dispatch` — no `issues:` event and no cron — so an
  agent-authored issue or a scheduled slot cannot launch an LLM pipeline by itself
- **Test:** tests/test_workflows.py::test_issue_bot

#### Scenario: the dispatch-only alarms still sweep when dispatched

- **Given** `queued-alarm.yml` (dispatch-only) and the sweep alarm
- **When** the dispatched sweep runs while the newest dispatched sweep delivery is FAILED
  or still HUNG in flight past the cap
- **Then** `make sweep-alarm` exits 1 naming it, and "no delivery owed" reports OK
- **Test:** tests/test_sweep_alarm.py::test_a_dispatch_only_sweep_owes_no_weekly_slot
