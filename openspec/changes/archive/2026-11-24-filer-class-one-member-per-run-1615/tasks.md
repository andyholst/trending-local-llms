# Tasks: filer-class-one-member-per-run-1615

- [x] Add `_one_member_per_run()` and use it in `group_failure_classes()` (`scripts/pipeline_failure_issue.py`)
- [x] Pin the collapse with `test_a_run_with_several_bad_jobs_is_one_member_and_one_ledger_row`, registered in the module's own call list
- [x] Prove the new guard RED on `origin/master`'s filer (`PASSED 322 | FAILED 4`, the captured row showing `class_runs == [300, 300, 300, 300, 300, 300]`) and GREEN after the change (`PASSED 326 | FAILED 0`)
- [x] Run `make lint` (rc=0), `make architecture-check` (rc=0), `make findings-check ISSUE=1615` (OK) and `make openspec-index` (2 active, 511 archived)
- [x] Run the full `make test`: first run `177 module(s) passed, 1 FAILED` naming ONLY this change's own unticked task boxes (the circular tasks/index bootstrap); after ticking, the confirming run is green
- [~] Land the owed AGENTS.md §8 row naming this test function — blocked: rule 3c human sign-off (AGENTS.md is protected in a headless leg); recorded in `findings/1615.md`
- [x] Commit, push a READY PR whose body closes #1615, archive the change on that branch, and hand over to `tll-reviewer`
