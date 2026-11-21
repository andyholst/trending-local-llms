# Tasks: engine-guide-sync (#1220, PR #1222)

- [x] T1: read-only checker for guide rows, matrix columns, registry and measured engines; named drift findings.
- [x] T2: Makefile target + `_validate-search` wiring so refreshes fail when the lists drift.
- [x] T3: tests/test_engine_guide_check.py 14/14 incl. planted stale guide and matrix.
- [x] T4: PR opened and `make openspec-record-pr ISSUE=1220 PR=1222` run at the PR head.