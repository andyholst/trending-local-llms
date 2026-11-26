# Tasks — ci-keeper-ledger-45788860357

- [x] Append the diagnosed ledger row for run 45788860357 with fix_pr #1777 and collected guard `tests/test_openspec_archive_check.py`
- [x] Confirm `make pipeline-failure-guard-check` exits 0 on the branch head (no #1763 missing-row red)
- [x] Confirm the guard verdict is green on the branch head and both spec-referenced tests exist in the collected module (full suite is CI-only per #1423)
- [x] Declare this tracked change so the lifecycle gate binds #1784; regenerate OPENSPEC.md
- [x] Add findings/1784.md with the measured evidence
