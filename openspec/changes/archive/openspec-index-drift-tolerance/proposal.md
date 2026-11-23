# Proposal: openspec-index-drift-tolerance

Issue: #1415
PR: #1419

## Why

`make openspec-index-check` re-rendered `OPENSPEC.md` from disk and failed on ANY byte difference, so a merged PR that archives its change left the committed index stale by one row or one count line and reddened the gate on nearly every merge (measured on master `22072e92`: the file said 452 archived while disk held 453). Housekeeping drift of that size is not a broken index; failing on it turned every merge into a red pipeline.

## What Changes

- `scripts/openspec_index.py` gains ONE constant, `MAX_OPENSPEC_INDEX_DRIFT = 25`, and ONE drift measure, `index_drift()`, counting rows on disk with no row + rows for changes that no longer exist + rows whose data changed + the count-line drift. `--check` reds only above the threshold, and at or under it prints a `WARN` naming the drift and exits 0. A MISSING `OPENSPEC.md` still reds, and `--write` is unchanged.
- `scripts/openspec_index_repair.py` (the #304 keeper) classifies with the SAME `index_drift()` / `MAX_OPENSPEC_INDEX_DRIFT`, so a tolerated drift is still named, counted and rewritten instead of silently accumulating.
- Tests: the exact 25 vs 26 boundary, a count-line-only drift, a single changed row, a missing index, the counting rule, and keeper consistency. The auto-merge-rebase fixture's small squash-tree drift becomes a tolerated WARN rather than a RED.

## Impact

No schema, contract, API, table or data-shape change. `--write` output is byte-identical to before; the check merely stops failing on drift at or under the threshold. The gate still reds on a missing `OPENSPEC.md` and on more than 25 differing changes.

## Not covered

- No change to the ACTIVE-backlog ceiling (`MAX_ACTIVE_OPENSPEC_CHANGES`, issue #938).
- No workflow, schedule or cron edit; no merge and no master push.
