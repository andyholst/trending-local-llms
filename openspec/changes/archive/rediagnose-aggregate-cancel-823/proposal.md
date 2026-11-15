# Rediagnose the cancelled refresh-bot aggregate row (issue #823)

Issue: #823
PR: #983

## Why

Issue #823 was filed UNDIAGNOSED: the pre-#923 log reader refused the job log of
`refresh-bot` run 41929086636 (job 126926297445, `aggregate`, concluded `cancelled`), so its
ledger row carries no `fix_pr` and no `guard`. The log is readable now: the refresh was HEALTHY
up to the cancel point — store QA `OK: no duplicate models (117 unique)`, unit suite
`PASSED 124 | FAILED 0` — and the delivery was terminated by an EXTERNAL
`##[error]The operation was canceled.` inside the `Commit + open PR if changed` step. A
`cancelled` scheduled delivery is exactly the class the landed alarms already track and grade
red (issue #801, fixed by PR #806, guarded by `tests/test_sweep_alarm.py`). Re-diagnosing the
row onto that landed fix is ledger proof, not new implementation work for a fixed class (rule 6r).

## What Changes

- The ledger row for run 41929086636 is raised append-only: `fix_pr: 806`,
  `guard: "tests/test_sweep_alarm.py"`, `error_excerpt` (the bounded log block, scrubbed),
  `rediagnosed_utc`, `rediagnosis_note`; the original `undiagnosed` field is KEPT (rule 3b) and
  `targets: []` stays — the filing itself justified it ("the log names no `make` target").
- `tests/test_pipeline_failure_guard.py` gains
  `test_run_41929086636_is_rediagnosed_onto_the_cancelled_delivery_guard` asserting the row and
  the post-merge gate shape with #823 CLOSED.
- Issue #823 closes on this row via the PR's closing binding.

## Impact

- `data/pipeline_failures.json` — one row raised (added keys, nothing removed).
- `tests/test_pipeline_failure_guard.py` — one test function + its `main()` call.
- Affected capability: `alarms`.

## Not covered

- No repo-side code fix: the cancellation came from outside the pipeline (no concurrent
  refresh-bot run in the window; the workflow's own concurrency is `cancel-in-progress: false`).
  Hunting who cancelled a November 4 scheduled run is not repo work.
- The sibling UNDIAGNOSED rows of the SAME cancel class (if later sweeps file more) are re-diagnosed
  the same way — each rides its own change.
