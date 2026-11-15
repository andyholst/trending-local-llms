# Re-diagnose the issue-bot record-pr refusal row (issue #831)

Issue: #831

## Why

Issue #831 was filed UNDIAGNOSED: the pre-#923 log reader refused the job log of `issue-bot`
implement run 43108536309 (job 130818528159), so its ledger row carries no `fix_pr` and no `guard`
(rule 6r shape unmet). The log is readable now: the run's final step died with
`[openspec-record-pr] REFUSED: no change — active or archived — references Issue: #615 — nothing
recorded` / `make: *** [Makefile:347: openspec-record-pr] Error 2` — the change had been created
WITHOUT its `Issue:` binding, so the record step noticed only at the END of the run. That is the
exact class #952 describes, landed as PR #955 (`make openspec-binding-check` bundled into `make
openspec-check`, so an unbound ACTIVE change goes red at the gate before an implementation can
waste its window), guarded by `tests/test_openspec_binding.py`. Re-diagnosing the row onto that
landed fix is ledger proof (rule 6r).

## What Changes

- The ledger row for run 43108536309 is raised append-only: `fix_pr: 955`,
  `guard: "tests/test_openspec_binding.py"`, `error_excerpt` (the bounded log block),
  `rediagnosed_utc`, `rediagnosis_note`, and `targets` GROWN `["Makefile:347: openspec-record-pr"]`
  (the log names the target — rule 3b growth only, nothing removed); the original `undiagnosed`
  field is KEPT.
- `tests/test_pipeline_failure_guard.py` gains
  `test_run_43108536309_is_rediagnosed_onto_the_landed_openspec_binding_fix` asserting the row and
  the post-merge gate shape with #831 CLOSED.
- Issue #831 closes on this row via the PR's closing binding.

## Impact

- `data/pipeline_failures.json` — one row raised (added keys, grown `targets`, nothing removed).
- `tests/test_pipeline_failure_guard.py` — one test function + its `main()` call.
- Affected capability: `alarms`.

## Not covered

- No new repo-side fix: the refusal was the guardrail WORKING; the missing binding is what #955's
  binding-check now catches at the gate.
- Whether the sweep should have re-picked the (already-closed) target at all is a queue-state
  question tracked by the landed `already-fixed` re-read (#522, `issue-bot-already-fixed` marker) —
  not this row's failure.
