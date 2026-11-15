# Only the refresh cron stays active — every other cron job inactivated; LLM calls only through the harness image (owner directive)

**Issue:** [#1029](https://github.com/andyholst/trending-local-llms/issues/1029)
**Capability:** `fleet-cadence` (modified), `alarms` (added), `merge-gate-no-llm-calls` (new)

## Why

The owner directive of 2026-11-15: "the main CI pipeline should only run the unit tests
and tests, never real LLM calls — that is only for the other CI pipelines / bots that
only the owner, collaborator or the GitHub bot can start", and "main LLM calls are only
executed from the host/agents Hermes harness-image setup", and "only the refresh cron
stays active — every other cron job is inactivated".

The fleet had drifted into scheduled model work: `issue-bot.yml` auto-started an
implementer on EVERY opened issue carrying a bot label (a bot-authored issue could start
a 30-minute LLM pipeline), `issue-review-bot` and `code-review-bot` ran weekly model
reviews on cron, `architecture-bot`, `bot-health`, `pr-health` and `queued-alarm` all
carried cron slots, and qa-validate's `live-smoke` gated `auto-merge` on a real Hermes
call (`make hermes-smoke`). A merge gate must be deterministic; LLM work must start only
where the owner (or a collaborator, or the bot-to-bot dispatch) admits it through a
`guard`, and only inside the harness-image containers the Makefile launches.

## What Changes

- `refresh-bot.yml` is the ONLY pipeline left with an `on.schedule` (weekly Wednesday
  `'0 6 * * 3'` + `'43 17 * * 3'` backup — unchanged).
- `issue-bot.yml` loses `on: issues: [opened]` AND its sweep crons (`'19 * * * 3'` +
  backup `'49 * * * 3'`); it becomes dispatch-only (issue number, or empty = sweep).
- `issue-review-bot`, `architecture-bot`, `bot-health`, `code-review-bot`, `pr-health`
  and `queued-alarm` lose their `schedule:` blocks; each keeps owner `workflow_dispatch`.
- `qa-validate.yml` drops its `make hermes-smoke` step from `live-smoke`; the
  deterministic `make search-smoke` fetch smoke stays. No `hermes` / agent target may
  appear anywhere in qa-validate.
- `scripts/sweep_alarm.py` derives the owed-delivery mode from the workflow tree
  (`workflow_declares_schedule`): a dispatch-only sweep owes no weekly slot (age alone
  never reds it), while a FAILED or HUNG dispatch still goes red; scheduled-mode
  semantics stay unchanged.
- `AGENTS.md` gains rule 6t (cadence + LLM-call control) and its §6b/§6e/§6j/§6l/§8 rows
  are updated to the dispatch-only fleet.
- Tests pin it: `test_only_the_refresh_pipeline_carries_a_schedule`, the
  `test_qa_validate` NO-hermes-smoke / NO-agent-target checks, the dispatch-only sweep
  alarm tests, and the flipped workflow pins in `test_bot_health` / `test_architecture_bot`.

## Impact

- Pipelines: issue-bot, issue-review-bot, architecture-bot, bot-health, code-review-bot,
  pr-health, queued-alarm — cron + issue-event triggers removed.
- Gate: qa-validate `live-smoke` no longer executes a model call.
- Scripts: `scripts/sweep_alarm.py`; tests: `test_sweep_alarm.py`, `test_workflows.py`,
  `test_bot_health.py`, `test_architecture_bot.py`, `test_agents_rows.py`.
- `ARCHITECTURE.md` §10 regenerated; README bot-cadence prose regenerated.

## Not covered

- The Makefile search/fix/implement targets themselves are unchanged — they remain the
  only way a model call executes (rule 6c/6p), and refresh-bot's scheduled search legs
  keep running inside the harness image exactly as before.
- The freshness-alarm window comment in `queued-alarm.yml` ("twice-daily crons … 14 h")
  is measured drift, filed as a separate finding (rule 6g), not fixed here.
