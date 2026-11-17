# Change: normalise-ledger-target-form-1054

Issue: #1054

## Why

`make pipeline-failure-issue` stored a ledger row whose target kept the Makefile's own decoration
from the log's bracketed failure line: run 43109817750 carried
`"targets": ["Makefile:1384: sweep-alarm"]`, while every sibling sweep-alarm row
(#820/#821/#822/#824/#829) carries the bare, parseable `["sweep-alarm"]`. The ledger PR body
(`compose_ledger_pr_body`) and the filing body's reproduction line render `targets` as
`make <target>` — `make Makefile:1384: sweep-alarm` is not a runnable command and the token reads
like a line reference rather than the target a reviewer can act on (rule 6m: the reproduction
command is `make <target>`). A row filed in the warped form was never re-normalised, so the ledger
was not uniformly parseable.

## What Changes

- `scripts/pipeline_failure_issue.py` gains the ONE `normalize_target` seam: the bracketed
  `file:<line>: <name>` form becomes the bare `<name>`; a bare name passes through unchanged.
  `failed_make_targets` runs BOTH captures through it, so every future filing, ledger row and
  quoted reproduction command carries the parseable target.
- The re-diagnosis raise (issue #969's pass) re-normalises the WHOLE grown targets list of the
  raised row — its pre-existing entries included — so a row that comes out of a raise is uniform
  with its sibling rows.
- Each sweep runs one convergence pass (`normalize_ledger_targets`) over the stored ledger: warped
  rows' targets become the bare form, every run id survives untouched (rule 3b: nothing removed,
  no re-spelling), and a ledger that is already uniform is NOT rewritten — no churn, no diff noise.

## Impact

- Capability: `alarms` (the pipeline-failure filer's target recording).
- Data: `data/pipeline_failures.json` converges on the uniform target form on the next sweep.
- Tests: `tests/test_pipeline_failure_issue.py` locks the pure normaliser, the sweep convergence
  pass and the raise's re-normalisation.

**Not covered:** the guard check (`pipeline_failure_guard_check`), marker shapes, filing
semantics, and the ledger PR body's layout are unchanged; existing filed issue bodies are never
rewritten (bot threads are append-only).
