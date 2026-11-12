# Retire the fix-bot repair pipeline completely

**Issue:** [#814](https://github.com/andyholst/trending-local-llms/issues/814)
PR: #815
**Capability:** `pipeline-repair`

## Why

The owner directed (2026-11-11): "the fix bot repairer pipeline must be disabled
completely, that its .yml file." The repairer had outlived its value: every measured
fix-bot round of the last weeks either detached without answering (runs 39079759124,
40177729642), reported success over an unpushed change, or repaired conflicts a rebase
would have prevented at the source. The repo already carries the one repair loop that
works — the implementer's own (§6d fix loop inside `issue-bot.yml`, run by
`scripts/fix_loop.sh` with a real transcript and a monitored PR). A second agent
loop dispatched *after* a PR went red is the weaker copy of the same job, and its
dispatch surface (`qa-validate -> dispatch-fixbot`, `pr-health -> Dispatch the repair`)
is a `workflow_dispatch` trigger an outside re-run can hit.

## What Changes

- **Delete `.github/workflows/fix-bot.yml`** — the pipeline, its guard, its dispatch
  trigger and its `workflow_run` trigger are gone from the tree.
- **`qa-validate.yml`** — the `dispatch-fixbot` job is removed. A red `validate` stays
  red; its `qa-report.txt` artifact is the handoff to a human or the next implementer.
- **`pr-health.yml` + `scripts/pr_health.py`** — the sweep becomes report-only: it
  flags every silent PR and comments the remedy, and dispatches nothing. The
  `MAX_FIXBOT_COMMITS` variable leaves with the repairer.
- **`refresh-bot.yml`, `issue-bot.yml`, `queued-alarm.yml`, `publish-agent-image.yml`**
  — every prose/hint line that told a reader to "dispatch fix-bot" is restated.
- **`Makefile`** — no target dispatches the retired pipeline; the fix-loop recipes stay
  (they belong to the implementer).
- **`scripts/fix_pr.py`, `scripts/check_fix_bot_loop.py`** stay as the implementer's
  repair helpers, renamed in their docs to name their ONE remaining caller.
- **AGENTS.md** (rule 3c review-required): §6b pipeline list loses the fix-bot line;
  §6j marker table loses the `fix-bot` row; §8 guard rows restate who owns each lesson.

## Impact

- Affected specs: `pipeline-repair` (retired requirement + survivor rules).
- Affected pipelines: `qa-validate.yml`, `pr-health.yml`, `refresh-bot.yml`,
  `issue-bot.yml`, `queued-alarm.yml`, `publish-agent-image.yml`.
- Affected tests: `tests/test_workflows.py` (retirement guard),
  `tests/test_pr_health.py`, `tests/test_fix_loop.py`, `tests/test_architecture.py`,
  `tests/test_secret_output.py`, `tests/test_nerve_key_wiring.py`.
- **Not covered:** no replacement repair pipeline is created; the implementer's fix
  loop and `master-alarm`/`queued-alarm` remain the repair/notice paths. Rotating the
  `FIXBOT_DISPATCH_TOKEN` secret is a human action (the name survives for checkout
  PATs; see findings).
