# Tasks — none-title-backfill-1759 (issue #1759)

- [x] Measure the board read-only: 55 open issue titles carry `None /`, all with a `pipeline-run-failure … run=<id>` marker
- [x] Resolve the authoritative REST `.name` for all 55 run ids (53 qa-validate, 2 refresh-bot; 0 unresolved)
- [x] Patch all 55 issue titles/bodies in place via `gh api -X PATCH`; verify 0 `None /` titles remain and markers survive
- [x] Additively backfill `workflowName` onto all 85 ledger rows from REST `.name`; prove zero removed/changed keys or values (rule 3b)
- [x] Add `test_the_committed_ledger_carries_a_real_workflow_name_per_row` to the existing filer test module; PASSED 369 | FAILED 0
- [x] RED-prove the guard against the pre-backfill ledger (1 FAIL: `broken=[...]`, then restored from copy)
- [x] OpenSpec change: proposal, `pipeline-failure-filer` spec with Test lines, this checklist; index regenerated
- [x] `findings/1759.md` present with the owed §8 row; fast offline checks run (targeted module, `make lint`)
- [~] Commit on the issue-named branch, push, open a non-draft PR closing #1759; containerised `make validate` / full `make test` are CI-only — blocked: qa-validate runs on the pushed head
