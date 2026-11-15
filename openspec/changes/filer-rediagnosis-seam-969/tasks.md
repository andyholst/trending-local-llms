# Tasks: filer-rediagnosis-seam-969

- [x] Add the re-diagnosis pass to `scripts/pipeline_failure_issue.py` (`rediagnose_undiagnosed`,
  called from `sweep()` after the filing loop; append-only row raise, loud retry, dry preview)
- [x] Add the three lock tests to `tests/test_pipeline_failure_issue.py` and wire them into `main()`
- [x] Update the two `ARCHITECTURE.md` descriptive rows for `pipeline-failure-issue` /
  `scripts/pipeline_failure_issue.py` to name the re-diagnosis pass (rule 6h)
- [x] Gates green in the same change: `python3 tests/test_pipeline_failure_issue.py`,
  `python3 tests/test_pipeline_failure_guard.py`, `make lint`, `make openspec-check`,
  `make secret-scan`, `make findings-check`
