# Proposal: r-marker-workflow-1288

Issue: #1288
PR: #1293

## Why

A `success` run conclusion can be a `guard`/`closure`-only duplicate, not a full
`qa-validate`: run `45016049444` was the only full validation on PR #1267's head
and ended `cancelled`, yet `gh run list` also reported two runs on the SAME head as
`success` whose job set was only `guard` + `closure`. The monitor's
`R:<run>:<status>:<conclusion>` marker and the conclusion column both say `success`
for a run that never executed the validating jobs, so a fleet reader can call a PR
green from the signal alone.

## What Changes

- Extend `scripts/watch_monitor.py` so each `R:` marker carries an ADDITIONAL,
  colon-safe workflow-name token when the run row provides `name` (e.g.
  `R:<id>:<status>:<conclusion>:pr-closure`). Existing fields are unchanged; a run
  row with no name emits the original marker (rule 3b additive).
- Add a guard in `tests/test_watch_monitor.py` proving a `guard`/`closure`-only
  `success` is distinguishable from a full `qa-validate` `success` from the marker
  alone, and that the token cannot inject a colon into the marker shape.

## Impact

One script edit, one test module. No new target, script, data/contract format,
image or pipeline job. The core marker shape (`id`, `status`, `conclusion`) is
unchanged, so this needs no `AGENTS.md` rule change.

## Not covered

- No change to CI dispatch, merge behaviour, branch protection or access.
- No rewriting of the rulebook's marker description; the extra field is optional
  and backward-compatible.
