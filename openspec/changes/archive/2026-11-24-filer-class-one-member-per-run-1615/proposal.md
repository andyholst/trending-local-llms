# Proposal: filer-class-one-member-per-run-1615

Issue: #1615

## Why

`group_failure_classes()` (landed by #1557) keeps EVERY item as a group member, and `sweep()`
builds one item per (run, job). A single run can conclude with SEVERAL bad jobs — measured on
merged master, qa-validate push run 45380383434 carried SIX cancelled jobs (`validate`,
`live-smoke`, `invalid-change-repair`, `architecture-repair`, `announce-fallback`,
`index-repair`). The `make pipeline-failure-issue DRY=1` sweep therefore printed
`WOULD FILE: class da39a3ee5e6b on 20 run(s) 45380383434, 45380383434, …` and the ledger loop
would append one row PER ITEM — six rows with the same `run_id`. That breaks the filer's own
one-row-per-run contract and every reader that keys on the run id (the guard, the stamp pass
#1099, the attribution pass #1053, `rediagnose_pending` #1136), and it inflates the class's
reported scope.

## What Changes

- `scripts/pipeline_failure_issue.py`: new `_one_member_per_run()` collapses every class group to
  ONE member per run id (the earliest job of that run); `group_failure_classes()` uses it for the
  member set, the dedup key and the recorded members. One issue per class, one ledger row per run.
- `tests/test_pipeline_failure_issue.py`: new
  `test_a_run_with_several_bad_jobs_is_one_member_and_one_ledger_row`, planting one run with SIX
  cancelled jobs of one class and asserting one issue, exactly one ledger row, `class_runs == [300]`
  and a body that claims no further member runs.

## Impact

Behaviour-narrowing only. A class whose runs each have one bad job is unchanged; a class whose runs
have several bad jobs now files one row per run instead of one per job. No existing ledger key or
value is removed. The new test function is not yet named by AGENTS.md §8 — that row is owed to a
human sign-off and declared in `findings/1615.md` (rule 3c).

## Not covered

- The PR-blockage half (#1164/#1476): it already groups by shape across branches and was measured
  to file once per defect; this change does not touch it.
- De-duplicating runs already present in the shipped ledger from the pre-#1615 sweeps: those rows
  stay as they are (append-only, rule 3b).
- No new make target, no workflow wiring, no CI dispatch, no merge, no master push.
