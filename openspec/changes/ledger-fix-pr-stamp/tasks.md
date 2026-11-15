# Tasks — ledger-fix-pr-stamp

- [x] Stamp implemented in `scripts/openspec_record_pr.py` (plan-before-mutation, surgical additive fills, guard KEEP/FILL/REFUSE)
- [x] New suite `tests/test_ledger_fix_pr_stamp.py` locks every shape (stamp, guard-keep, guard-fill, refusal-writes-nothing, no-row no-op, already-raised untouched, archived re-run, wiring) — 24/24 checks green
- [x] `ARCHITECTURE.md` target + §6 rows updated and the generated block regenerated (`make architecture-refresh`), `make architecture-check` green
- [x] `make lint`, `make openspec-index` + `make openspec-index-check` green on this head; full `make test` re-run green after these boxes ticked
