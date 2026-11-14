# Proposal: readme-bot-cadence-863

Issue: #863

## Why

The generated README still describes the bot queue as running "per hour" /
"hourly" and the queued-alarm as "twice an hour at `:07`/`:37`", and the
code-review block says "weekly Monday `07:23`" — while every scheduled
pipeline is pinned weekly on Wednesday (`tests/test_workflows.py`, issues
#670–#677) and `code-review-bot.yml` actually schedules `7 6 * * 3`
(Wednesday 06:07 UTC). A README that misstates when the bots run makes the
automation undocumented, not just unexplained (its own cited reason).

## What Changes

- `scripts/update_trending.py` render template: the `issue-bot`/`issue-review-bot`
  queue block now states the weekly Wednesday sweep (`19 * * * 3` + `49 * * * 3`
  backup) and the shared two-label queue; the `queued-alarm.yml` block states
  `37 * * * 3`; the `code-review-bot.yml` block states `7 6 * * 3` (Wednesday
  06:07 UTC). `README.md` regenerated with `make render-readme`.
- New validator check `check_readme_bot_cadence` (readme stage): a README line
  naming a scheduled pipeline that claims an hourly cadence, a non-Wednesday
  weekday, or quotes a cron the named workflow does not schedule — FAILS.
- New suite `tests/test_readme_bot_cadence.py` runs the real check against
  planted fixture READMEs (each wrong shape MUST go red) and the real repo
  README + template (green).

## Impact

- `scripts/update_trending.py` (template), `scripts/validate.py` (check +
  readme-stage registration), `README.md` (generated), `tests/`
- AGENTS.md §8 guard row

## Not covered

- No pipeline or cron changes — the pipelines already match; only the prose
  was stale, plus the check that keeps it matched.
