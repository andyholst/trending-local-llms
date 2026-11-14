# Weekly, Wednesday cadence for the whole scheduled fleet

**Issues:** #670 (refresh-bot), #671 (issue-bot), #672 (issue-review-bot), #673
(architecture-bot), #674 (bot-health), #675 (queued-alarm), #676 (pr-health),
#677 (code-review-bot) — the owner's `weekly-cadence` directive, implemented in ONE
coordinated change.

## Why

The owner asked that ALL periodic work stop its fine-grained cadence and run ONCE a
WEEK on Wednesday: the data-gathering (`refresh-bot`) — which every other bot's work
derives from — either once or twice on that one day, and every pipeline that had a
`schedule` the same way. The previous cadence was the opposite end of the spectrum —
`refresh-bot` daily, `issue-bot`/`issue-review-bot` hourly, the alarms twice-an-hour or
four-times-a-day — so cutting it to one day a week is a deliberate reduction in the
periodic GitHub Actions load the repo's crons cause, and one day for the whole fleet to
measure and react. The eight issues each carry one pipeline's target; the shared
`* * 3` day keeps them coherent.

## What Changes

For each scheduled pipeline, the `on.schedule` crons move to Wednesday (`* * 3`), and
the shared cadence-coupled config follows:

- `refresh-bot.yml`: `0 6 * * *` + `43 17 * * *` → **twice on Wednesday**, `0 6 * * 3`
  + `43 17 * * 3`.
- `issue-bot.yml`: `19 * * * *` + `49 * * * *` → `19 * * * 3` + `49 * * * 3`.
- `issue-review-bot.yml`: `41 * * * *` → `41 * * * 3`.
- `architecture-bot.yml`: `13 * * * *` → `13 * * * 3`.
- `bot-health.yml`: `23 */6 * * *` → `23 * * * 3`.
- `queued-alarm.yml`: `7,37 * * * *` → `37 * * * 3`.
- `pr-health.yml`: `23,53 * * * *` → `53 * * * 3`.
- `code-review-bot.yml`: `23 7 * * 1` → `7 6 * * 3`.

Because the alarms measure "how long since the last delivery", their windows follow the
cadence: `freshness_alarm.py` `DEFAULT_MAX_AGE_HOURS` 14 → 170 (one week + a day's
slack) and `sweep_alarm.py`'s default 3 → 168, its Wednesday slot counting, and its
"slots missed" logic now counts Wednesday deliveries.

The rulebook (`AGENTS.md` §6b/§6j/§6e, §8), `ARCHITECTURE.md` §4 and the GENERATED §10
inventory, and the tests that pinned the old minutes (`tests/test_workflows.py`,
`tests/test_architecture_bot.py`, `tests/test_sweep_alarm.py`,
`tests/test_freshness_alarm.py`) all move with them.

## Impact

The eight workflow files, the two alarm scripts, `AGENTS.md`, `ARCHITECTURE.md` (prose
+ the regenerated §10 block), `tests/test_workflows.py`, `tests/test_architecture.py`
(regen-driven), `tests/test_architecture_bot.py`, `tests/test_sweep_alarm.py`,
`tests/test_freshness_alarm.py`, this change and the regenerated `OPENSPEC.md`.

## Not covered

- The EVENT-driven pipelines (`qa-validate.yml`, `fix-bot.yml`, `pr-closure.yml`,
  `publish-agent-image.yml`) have no `schedule` and are untouched: a PR or a dispatch
  still triggers them the moment it happens — the "once a week" ask is about the crons.
- The alarm LOGIC (what is loud when red) is unchanged; only the cadence it measures
  moves. A weekly `bot-health` means a red weekly cron is caught the next Wednesday, not
  within hours — the owner accepted that trade-off explicitly when choosing "all weekly".
