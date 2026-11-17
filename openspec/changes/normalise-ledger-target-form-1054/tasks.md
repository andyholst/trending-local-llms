# Tasks: normalise-ledger-target-form-1054

- [x] `scripts/pipeline_failure_issue.py`: `normalize_target` seam + `failed_make_targets`
      normalises BOTH captures (file:line bracket form → bare target; bare passes through) —
      verified by the pure-format test (red on old code: `make: *** [Makefile:1231: validate]`
      kept the decoration; green now: both forms → `["validate"]`).
- [x] Sweep convergence pass `normalize_ledger_targets`: warped stored rows normalise, every run
      id survives, uniform ledger stays byte-identical (no churn) — verified by the end-to-end
      sweep test (red on old code: `targets normalised` line absent, warped row unchanged).
- [x] Re-diagnosis raise re-normalises the WHOLE grown targets list — verified by the planted-row
      test (red on old code: raised row kept `["Makefile:1384: validate", "validate"]`).
- [x] `tests/test_pipeline_failure_issue.py`: three tests + scene ledger warped row extended.
- [x] `make openspec-index && make openspec-index-check` green.
- [x] `make openspec-check` green (change validates, binding, backlog headroom).
- [x] `make test`, `make lint`, `make secret-scan` green.
- [x] AGENTS.md §6r + §8 row and ARCHITECTURE.md §8 row updated in this change.
- [x] PR opened (five-section body, closes #1054); change archived at the PR head.
