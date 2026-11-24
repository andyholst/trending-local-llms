# Tasks: filer-error-class-grouping-1557

- [x] Add `group_failure_classes()` and the two-phase collect→group→file sweep in `scripts/pipeline_failure_issue.py`
- [x] Add the additive member-run sentence to `compose_body`/`file_issue` and the `failure_class` + `class_runs` ledger keys
- [x] Pin the grouping with `test_the_master_schedule_half_files_one_issue_per_error_class` and `test_the_error_class_dry_run_previews_without_writing`, registered in the module's own call list
- [x] Give the scheduled-cancellation fixture its OWN log so the pre-existing "two different failures file two issues" assertion stays true under grouping
- [x] Prove the new guard RED on `origin/master`'s filer (`PASSED 313 | FAILED 7`) and GREEN after the change (`PASSED 320 | FAILED 0`)
- [x] Run `make lint` (rc=0), `make architecture-refresh` + `make architecture-check` (rc=0), `make findings-check` (16 findings, OK) and `make openspec-index` (2 active, 505 archived)
- [x] Run the full `make test`: first run `174 module(s) passed, 1 FAILED` naming ONLY this change's own unticked task boxes (the circular tasks/index bootstrap); after ticking, the confirming run is green
- [~] Land the owed AGENTS.md §8 row for the two new test functions — blocked: rule 3c human sign-off (AGENTS.md is protected in a headless leg); recorded in `findings/1557.md`
- [x] Commit, push a READY PR whose body closes #1557, archive the change on that branch, and hand over to `tll-reviewer`
