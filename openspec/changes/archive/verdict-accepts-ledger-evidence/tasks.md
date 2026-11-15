# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/issue_verdict.py`: the evidence gate accepts a pipeline-failure ledger
      row (`data/pipeline_failures.json` + run id) as checkable ONLY when the ledger's
      row for that run names a merged `fix_pr` and an existing guard test — via
      `pipeline_failure_guard_check.read_ledger` / `guard_test_exists` (rule 6d), plus a
      `--ledger` override for a test to plant its own ledger
- [x] 3. `tests/test_issue_triage.py` gains
      `test_a_pipeline_failure_close_is_accepted_only_with_a_merged_ledger_row` planting:
      ledger-backed close with a merged row accepted; citing a run with no merged fix
      refused; an unknown run refused; a prose-only close refused
- [x] 4. OPENSPEC.md regenerated with the new active row (the generated index gates CI)
- [x] 5. The native gates green on host python3 (docker unavailable here): tasks-check,
      spec-tests-check, duplicate-check, backlog-check, binding-check, index-check, and
      `tests/test_issue_triage.py` green
- [~] 6. The `AGENTS.md` §8 row for this evidence-gate guard is landed — blocked: rule 3c
      human sign-off (a headless leg cannot write the protected rulebook; the full row is
      recorded verbatim in `findings.md` as this run's owed-row finding)
