# Tasks

- [x] Re-diagnose run 42973469114 from its readable job log (VERIFIED: `gh run view 42973469114 --log`, implement-job tail: record-pr REFUSED + `Error 2`; run pushed `ci/data-gap-527-…`, PR #777 merged 2026-11-11 11:41 UTC)
- [x] Raise the ledger row append-only (`fix_pr: 955`, `guard`, `error_excerpt`, `rediagnosis_note`; `undiagnosed` KEPT, `targets` grown)
- [x] Add `test_run_42973469114_is_rediagnosed_onto_the_landed_openspec_binding_fix` to `tests/test_pipeline_failure_guard.py` and its `main()` call
- [x] Guard suite green (`python3 tests/test_pipeline_failure_guard.py`)
- [x] `make pipeline-failure-guard-check` exit 0 on the branch
- [x] `make findings-check`, `make lint`, `make openspec-check`, `make secret-scan` green
- [x] Open the ready PR closing #825 and monitor its pipeline to green + auto-merge
