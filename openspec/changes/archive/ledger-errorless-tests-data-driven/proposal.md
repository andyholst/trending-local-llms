# Proposal: ledger-errorless-tests-data-driven

Issue: #1386
PR: #1387

## Why

Keeper PR #1384 (the scheduled sweep's append-only ledger update, issue #802) went red at
`validate` → `Run unit tests (in container)`: `159 module(s) passed, 2 FAILED:
test_pipeline_failure_guard.py test_pipeline_failure_issue.py` (qa-validate run 45150423877,
job 137610187014). Both failures are "shipped ledger" assertions that froze a **transient**
ledger shape: exactly five errorless rows, `12 diagnosed / 5 attributed-without-a-diagnosis`,
and a hard-coded `measured` set of five run ids (#1039-#1043). The keeper PR correctly ran the
#969/#1136 re-diagnosis pass, raising `error_excerpt` into those five rows and appending four
new diagnosed rows (#1380-#1383); the gate then reported `17 diagnosed... 0 attributed` and the
selector returned `pending=[]`. The pipeline did exactly what #1136 asks, and the tests went red
because they encoded the pre-diagnosis snapshot. Rule 6b: a data-shape change must update its
tests; the keeper generator only commits the ledger.

## What Changes

- `tests/test_pipeline_failure_guard.py::test_the_committed_ledger_classifies_its_errorless_rows`
  derives the expected errorless fix-claimed set and the diagnosed/attributed counts from the
  shipped row dicts (independently of the gate's own predicate), then asserts the reported set
  and the summary against those values.
- `tests/test_pipeline_failure_issue.py::test_the_committed_ledger_s_errorless_rows_are_exactly_the_pending_set`
  derives the expected pending set from the row dicts (no error block under either spelling, not
  already raised, not terminal `log_expired`) and asserts it against `F.rediagnose_pending`.
- Both modules keep running the REAL seams on the REAL shipped ledger; the only stand-in is the
  independent expectation calculation, never the system under test (rule 6m).

## Impact

Tests only. No production seam, Makefile target, workflow, contract or image changes. The #1136
invariant is strengthened: an attributed row with no error block is still reported (never
silently assumed diagnosed), regardless of how many rows have been diagnosed. Verified 68/68 on
master's ledger (5 errorless rows) and on PR #1384's ledger (0 errorless rows).

## Not covered

- The ledger append itself in PR #1384 — that is the sweep's keeper change, not this fix. Once
  this fix lands on master, #1384 rebases onto it and its `make test` goes green.
- The re-diagnosis pass's extraction logic (#969/#1136) — out of scope; it behaved correctly.
- No `AGENTS.md` rule changes; no rule-3c row is owed.
