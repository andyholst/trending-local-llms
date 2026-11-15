# Tasks

- [x] Verify the failure class is already fixed+guarded on the fetched base (`python3 tests/test_trending_for_your_card.py` → `PASSED 45 | FAILED 0` at HEAD AND at the run's own base d3d411632)
- [x] Raise the ledger row for run 43050447566 append-only (`fix_pr: 571`, `guard: "tests/test_trending_for_your_card.py"`, `rediagnosis_note`; `undiagnosed` KEPT, `targets` unchanged `["test"]`)
- [x] Add `test_run_43050447566_is_rediagnosed_onto_the_landed_trending_guard` to `tests/test_pipeline_failure_guard.py` and its `main()` call
- [x] Guard suite green (`python3 tests/test_pipeline_failure_guard.py` → `PASSED 90 | FAILED 0`)
- [x] `make pipeline-failure-guard-check` exit 0 on the branch (verdict: row 830 names a real fix PR + on-disk guard)
- [x] Regenerate `OPENSPEC.md` (`python3 scripts/openspec_index.py --write` → 3 active, 309 archived; the stale count line 307→309 fixed)
- [x] `python3 scripts/openspec_index.py --check` and `make findings-check` green (host-side)
