# Proposal: keeper-dedupe-liveness

Issue: #1303
PR: #1306

## Why

Rule 6q's event-driven keeper is the ONLY repairer for a generated-artifact gate that
goes red on a push to `master`, and its dedup exists so a sweep does not file the same
keeper twice. The dedup counts an open keeper as suppressing when it is MERGEABLE —
but a mergeable keeper whose checks NEVER ran is a tombstone, not a repairer. Measured:
`ci/openspec-index-repair-20261122T041000Z` (PR #1248) is `MERGEABLE` while
`gh pr checks` answers `no checks reported on the branch`, and three consecutive
push-to-master `qa-validate` runs died at `openspec-index-check` for the same drift.
The tombstone suppresses the fresh keeper that would have repaired `master`, so the gate
stays red and every open PR's `validate`/`live-smoke` reds with it.

## What Changes

- `scripts/keeper_pr.py::keeper_dedupe` reads each open keeper's `statusCheckRollup`
  beside its `mergeStateStatus` and classifies it `live` (required checks green or still
  running), `tombstone` (mergeable but no check objects, or a concluded non-success) or
  `unmergeable` (DIRTY/CONFLICTING). Only a `live` keeper suppresses a duplicate; a
  `tombstone` is named and a fresh keeper is filed against the current tip, exactly as an
  unmergeable one already is (#960).
- `tests/test_keeper_pr.py` drives the real seam with a stub `gh`: a green keeper
  suppresses, a checkless mergeable keeper does NOT, a red keeper does NOT, and a
  pending keeper still does.

## Impact

No data, contract, Makefile target, workflow or image change; the keeper sequence keeps
its exit-code contract (0 suppressed, 1 refused, 2 unavailable). A tombstone keeper is
now visible by name in the sweep log instead of silently pinning the gate.

## Not covered

- Repairing the count-line drift itself — measured already current on `master`
  (`OPENSPEC.md` 1 active / 413 archived matches disk at `3d84c98`).
- Retiring or closing the existing tombstone keepers; the gate reports, a human closes.
