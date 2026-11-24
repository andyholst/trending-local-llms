# Proposal: filer-error-class-grouping-1557

Issue: #1557

## Why

The master/schedule half of `make pipeline-failure-issue` filed ONE ISSUE PER RUN. Measured on
this repository at 2026-11-24T05:34–05:38Z, one sweep opened issues #1506–#1553 (47 issues in
~4 minutes) and **38 of the 47 named the SAME failing step**, `OpenSpec gate`; the planner's
re-grouping on #1557 confirmed it. A recurring state-gate red therefore buries the signal under a
backlog of near-duplicates, and every later sweep re-files it because nothing groups by error
class. The PR-blockage half already solves this for `pull_request` runs (`failure_shape`,
issue #1476); the master/schedule half never received the same treatment (#1476 deliberately left
it out of scope), so the defect was filed here rather than folded into the change that found it
(rule 6g).

## What Changes

- `scripts/pipeline_failure_issue.py`'s `sweep()` collects the diagnostics of every UNFILED
  run/job first, then groups them by STABLE ERROR CLASS through the SAME seam the PR-blockage
  half uses (#1476): `failure_shape` (failing step names + the `make` targets + the FAILING
  REGION's own lines with every run-specific token collapsed), with `exact_failure_shape` as the
  second axis and a strict-subset drop so one defect files once.
- ONE issue is filed per class per window, oldest run representative first; the body gains an
  additive sentence naming every other member run of the class.
- EVERY member run still appends its OWN ledger row (append-only, rule 3b), carrying two additive
  keys: `failure_class` (the stable shape) and `class_runs` (every member run id).
- `tests/test_pipeline_failure_issue.py` gains
  `test_the_master_schedule_half_files_one_issue_per_error_class` and
  `test_the_error_class_dry_run_previews_without_writing`, registered in the module's own call
  list; the shared fixture gives the scheduled cancellation its OWN log so the pre-existing
  "two different failures file two issues" assertion stays true under grouping.

## Impact

Additive and behaviour-narrowing only. A class of ONE run files exactly as before; a class of N
files once instead of N times, and every member keeps its ledger row, so the guard
(`make pipeline-failure-guard-check`), the stamp pass (#1099), the attribution pass (#1053) and
`rediagnose_pending` (#1136) read the same per-run rows they do today. No make target, workflow,
contract, data format, image or ledger key is removed or renamed; the two new ledger keys are
rulebook. The new test functions are not yet named by AGENTS.md §8 — that row is owed to a human
sign-off and declared in `findings/1557.md` (rule 3c: a headless leg cannot write the protected
rulebook).

## Not covered

- The PR-blockage half (#1164/#1476) — its grouping, threshold and branch scoping are unchanged.
- Closing or merging the existing flood issues #1506–#1553: each needs its ledger row to carry a
  merged fix PR + collected guard, so the filer's behaviour change does not retire them.
- Any dedup beyond the window: a class whose members all fall outside the window is not grouped
  retroactively; the marker reconcile still backfills a filed run individually.
- No new make target, no workflow wiring, no CI dispatch, no merge, no master push.
