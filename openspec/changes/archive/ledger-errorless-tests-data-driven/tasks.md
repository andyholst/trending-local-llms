# Tasks: ledger-errorless-tests-data-driven

- [x] Derive expected errorless/attributed set and counts in `tests/test_pipeline_failure_guard.py`, assert against them
- [x] Derive expected pending set in `tests/test_pipeline_failure_issue.py`, assert against `F.rediagnose_pending`
- [x] Keep both modules running the real seams on the real shipped ledger (rule 6m)
- [x] Register the renamed guard test in the module's hand-rolled `main()`
- [x] Verify both modules 68/68 on master's ledger (5 errorless rows) and on PR #1384's ledger (0 errorless rows)
- [x] Run `make lint`, `make architecture-check`, `make openspec-check`
- [x] Write `findings.md`, compose the five-section PR body with one closing keyword, open the PR, record and archive the change, push and monitor the checks
