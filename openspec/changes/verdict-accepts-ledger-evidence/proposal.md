# Proposal: verdict-accepts-ledger-evidence

Issue: #993 — "make issue-verdict refuses a close whose EVIDENCE is a ledger row, so
already-fixed pipeline-failure issues re-enter the queue"

## Why

A pipeline-failure issue (rule 6r) is closed with proof that lives in the LEDGER:
`data/pipeline_failures.json` carries the run id, the merged `fix_pr` and the `guard`
test. But `scripts/issue_verdict.py`'s evidence gate (`evidence_is_checkable`) only
accepts a `path:line`, a path with an extension, or a `make`/`python3`/`gh` command —
so a correct `close` verdict on an already-fixed pipeline-failure issue is REFUSED by
design: the run burns ~4 minutes, exits red, the outcome comment fires, and the issue
re-enters the pick queue for another run to rediscover the same answer (measured on
issue #824, run 43681625562).

## What Changes

- `scripts/issue_verdict.py`: the evidence gate gains a pipeline-failure-ledger shape.
  An `EVIDENCE:` naming `data/pipeline_failures.json` + a run id is checkable ONLY when
  the ledger resolved against the fetched base has a row for that run id that names a
  merged `fix_pr` and a guard test `make test` collects — via the ONE ledger reader,
  `pipeline_failure_guard_check.read_ledger` / `guard_test_exists` (rule 6d). A
  prose-only close, a ledger reference to an unknown run, or a run whose row names no
  merged `fix_pr` stays REFUSED. A `--ledger` CLI override lets a test plant its own
  ledger.
- `tests/test_issue_triage.py`: plants both shapes — a ledger-backed close citing a
  merged row is accepted and closes; one citing a run with no merged fix (or an unknown
  run) is refused, as is a prose-only close.

## Impact

- A dispatched already-fixed ledger issue ends `verdict=close` green instead of exit 2.
- The ledger shape is ADDITIVE to the evidence gate's accepted shapes; every existing
  evidence shape still works, and no issue with a live gap can be closed on prose.

## Not covered

- Changing what the ledger records (rule 3b, append-only) or when a `fix_pr` is written.
- Verifying the fix PR's merge state with a live `gh` call — the ledger only gains a
  `fix_pr` once the fix PR has landed, the same assumption the ledger gate itself makes
  (`pipeline_failure_guard_check`, rule 6r).
