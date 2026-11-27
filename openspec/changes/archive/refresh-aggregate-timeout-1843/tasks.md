# Tasks: refresh-aggregate-timeout-1843

- [x] 1. Measured refresh run 46044870416 on the fetched base `793bf6fa9b189d26832e554e9459f1cc8e1a6bf1`: aggregate started 18:00:22Z, cancelled 18:30:37Z in `Commit + open PR`; all prior jobs and aggregate validation steps green.
- [x] 2. Added `tests/test_workflow_guards.py::test_the_refresh_aggregate_timeout_allows_validation`, reading the SHIPPED YAML through the module's parser and pinning the aggregate job-level timeout to `60`; wired into `main()`.
- [x] 3. RED-first proof: the guard fails on the base file with `FAIL … ['30']` (rc=1, 46 passed / 1 failed) and passes after the fix (rc=0, 47 passed / 0 failed); `tests/test_workflows.py` reports 1507 passed / 0 failed and confirms every `test_*` is called from `main()`.
- [x] 4. Raised ONLY `.github/workflows/refresh-bot.yml` aggregate job `timeout-minutes` from `30` to `60`; verified a one-line workflow diff, no schedule edit, no other timeout, no new workflow, no data/README/schema change.
- [x] 5. Wrote `findings/1843.md` with Evidence / Why / Done when; this OpenSpec change (proposal, Given/When/Then spec with a pinned real test and all tasks ticked); regenerated `OPENSPEC.md`.
- [x] 6. Fast offline checks green: `make lint`, `make openspec-check`, `make openspec-index-check`, `make openspec-tasks-check`, archive check, findings check, commit authorship and PR body/closure checks.
- [x] 7. Pushed the branch with owner identity and opened a READY PR whose title AND body each carry `Closes #1843`; recorded the head sha on the issue and verified real CI jobs registered on it.
