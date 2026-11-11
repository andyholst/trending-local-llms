# A cron pipeline that is red on every run is loud

**Issue:** [#488](https://github.com/andyholst/trending-local-llms/issues/488)
**Capability:** `bot-alarms`

## Why

`pr-health` failed on **every** scheduled sweep for days (`sweep: failure`, e.g. run 39530945300)
with a traceback nobody saw — and the failing step was the one whose job is to make a silent PR
loud, so its silence removed its own alarm.

Each existing alarm reads a DIFFERENT silence: `queued-alarm` a job stuck in `queued` (#252),
`sweep-alarm` a sweep that was never delivered (#497), `pr-health` a PR whose checks never ran
(#475). **Nothing** read "this PIPELINE's own cron is failing", which is the level above all three.
Every bot here is a cron expected to be green; a red one is indistinguishable in the product from a
quiet one, and the longer it stays red the more of its guard rails silently stop existing.

## What Changes

- **`scripts/bot_health.py`** — derives the repository's **cron pipelines from the workflows
  themselves** (a `- cron:` line, trailing comment allowed), reads each one's newest N *scheduled*
  runs (`--event schedule`; a manual run proves nothing), and fails when the newest N all concluded
  in failure, naming the newest run URL.
  - a window SHORTER than N is **not** a failure (a pipeline added yesterday has not had N chances);
  - `gh` failing is **loud** (exit non-zero), never a clean bill of health;
  - `--limit 0` is refused (a check that checks nothing);
  - `--list` prints the pipelines, so the sweep cannot be vacuous.
- **`make bot-health`** — the one target, host-side (it needs `gh`).
- **`.github/workflows/bot-health.yml`** — cron `23 */6 * * *` + owner dispatch, a `guard` job
  FIRST (rule 6j), `contents: read` + `actions: read` only: **read-only**, no comment, no dispatch.
- **`tests/test_bot_health.py`** — a stub `gh` on PATH: all-red fails and names the URL, one green
  in the window stays quiet, a young pipeline is not red, `gh` down is loud, `--limit 0` refused,
  the pipeline list is derived and non-vacuous, and the workflow carries its guard + cron + target.
- **`tests/test_workflows.py`** — `bot-health.yml` added to `BOT_GUARDS` and to
  `DISPATCH_ONLY_COVERAGE`, so the pipeline cannot ship unguarded or unproved.

## Impact

A bot that quietly stops working now reds its own scheduled sweep within hours, naming the run to
open — instead of waiting for someone to notice the Actions tab.

## Not covered (out of scope)

- The alarm reports; it does not repair or dispatch. A red pipeline still needs a human (or the fix
  loop of a PR), which is the same contract as `queued-alarm`.
- Only `schedule` deliveries are read, so a pipeline that is red on `push`/`dispatch` only is not
  this alarm's business — filed as a finding with the shape it would need.
