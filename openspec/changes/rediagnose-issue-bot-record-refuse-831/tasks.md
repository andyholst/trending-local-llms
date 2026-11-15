# Tasks

- [x] Re-diagnose run 43108536309 from its readable job log (VERIFIED: the ledger row already carries
      `rediagnosed_utc` 2026-11-15T14:55:56Z quoting `[openspec-record-pr] REFUSED: no change — active or
      archived — references Issue: #615 — nothing recorded` + `make: *** [Makefile:347: openspec-record-pr] Error 2`)
- [x] Raise the ledger row append-only (`fix_pr: 955`, `guard: "tests/test_openspec_binding.py"`;
      `undiagnosed` KEPT, `error_excerpt`/`targets` untouched from the re-diagnosis pass)
- [x] Add `test_run_43108536309_is_rediagnosed_onto_the_landed_openspec_binding_fix` to `tests/test_pipeline_failure_guard.py` and its `main()` call
- [x] Guard suite green (`python3 tests/test_pipeline_failure_guard.py` — PASSED 90 | FAILED 0)
- [x] `make pipeline-failure-guard-check` exit 0 on the branch (rc=0, run 43108536309 guarded)
- [x] `make findings-check`, `make lint`, `make openspec-check` green (findings written; lint
      = final-newline on every changed file; openspec python gates: tasks/binding/duplicate/backlog/test-lines all OK; the
      container-bound `secret-scan` runs in CI on the pushed tree)
- [~] Open the ready PR closing #831 and monitor its pipeline to green + auto-merge — blocked: the `issue-bot` workflow opens, pushes
      and monitors this PR from the recorded change (rule 6n/6e); an agent never opens or merges a PR, and CI runs the
      container-bound `secret-scan` on the head.
