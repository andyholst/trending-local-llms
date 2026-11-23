# Proposal: watcher-files-red

Issue: #1376
PR: #1377

## Why

`AGENTS.md` §6w's `R:` duty is only "it diagnoses the job and posts the result on the thread".
Nothing files. The repo's filer seam (`make pipeline-failure-issue` →
`scripts/pipeline_failure_issue.py`) has exactly one caller — `queued-alarm.yml`, which is
owner-dispatched, and rule 6t forbids a cron. So a concluded-bad run is invisible until an
owner happens to dispatch the sweep.

Measured 2026-11-22: the `test_refusals_land_declaration.py` flake reddened `validate` on
every open PR's branch (`155`/`157` passed, 1 FAILED on #1318/#1324/#1330/#1297) — a
PR-blocking shape over issue #1164's ≥2-open-PR threshold — and **no issue was filed**.
Rule 6r says such a failure MUST become a tracked issue carrying its own error text.

The monitor is a pure change detector by design (no ledger, no `gh` writes), and it is the
only component that actually SEES the red run. The filing duty therefore belongs to the
woken lane, triggered by the `R:` marker.

## What Changes

- §6w's `R:` duty gains the filing half: a concluded-bad run of a MAIN pipeline
  (`qa-validate`, `refresh-bot`, `issue-bot`, `issue-review-bot`, `architecture-bot`,
  `queued-alarm`) or of a PR pipeline is filed through `make pipeline-failure-issue` (the ONE
  filer seam, rule 6d) and handed to `tll-implementer` — not merely diagnosed and posted.
- `tests/test_watch_monitor.py` pins the needle, so the duty cannot be dropped silently.

## Impact

Rulebook (review-required, rule 3c) plus one guard. No workflow, target, script, data or
contract change; the monitor's marker protocol is unchanged.

## Not covered

- A cron that files without a lane: rule 6t forbids it, and the owner directive makes the
  sweep a dispatch.
- Changing `scripts/pipeline_failure_issue.py`'s thresholds (#1164's ≥2-PR rule) — a
  reviewer ruling.
