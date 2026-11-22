# Tasks: pr-block-log-budget-1174

- [x] Add `PR_BLOCK_MAX_LOG_READS` + `bound_pr_block_runs` to `scripts/pipeline_failure_issue.py`
- [x] Cap `pr_triggered_failures` and record the skipped count
- [x] Announce the budget and skipped count from `record_pr_blockages`
- [x] Add the guard to `tests/test_pipeline_failure_issue.py`; prove it RED on the base script
- [x] Regenerate `OPENSPEC.md`; run `make openspec-check`, `make lint`, `make architecture-check` and the focused module
- [ ] Write `findings.md`, re-read the #1174 thread for a newer claim, and open a non-draft PR with exactly one closing keyword bound to #1174; record/archive the change on that branch
