# Tasks: filer-rediagnosis-log-expiry-986

- [x] Track an append-only `rediagnose_attempts` counter on still-unreadable ledger rows in
  `scripts/pipeline_failure_issue.py` and, at `MAX_REDIAGNOSE_ATTEMPTS`, stamp the TERMINAL
  `log_expired` state (loud once) and exclude the row from the pending set (issue #986)
- [x] Keep the two structural branches (no failed job, readable-but-no-error-line) reported and
  retried, never expired (#969); `undiagnosed` kept, nothing removed (rule 3b)
- [x] `--dry` previews `WOULD EXPIRE run <id>: …` and writes nothing
- [x] `scripts/pipeline_failure_guard_check.py` reports a `log_expired` row as its own shape,
  never red and never the closed-without-guard refusal
- [x] Add the lock tests to `tests/test_pipeline_failure_issue.py` and
  `tests/test_pipeline_failure_guard.py` and wire them into each `main()`
- [x] Gates green: `python3 tests/test_pipeline_failure_issue.py` (102/0),
  `python3 tests/test_pipeline_failure_guard.py` (83/0)
- [x] OpenSpec change dir `filer-rediagnosis-log-expiry-986` (proposal + GWT spec + tasks), index
  refreshed
- [x] Update the `ARCHITECTURE.md` descriptive rows for `pipeline-failure-issue`,
  `pipeline-failure-guard-check`, `scripts/pipeline_failure_issue.py` and
  `scripts/pipeline_failure_guard_check.py` to name the bound + the `log_expired` shape (rule 6h)
- [~] Update the AGENTS.md §8 rows for `tests/test_pipeline_failure_issue.py` and `tests/test_pipeline_failure_guard.py` to name the terminal `log_expired` state — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); the FULL row text is recorded as
  a findings.md `- **Owed-row:**` finding for `make file-findings`
