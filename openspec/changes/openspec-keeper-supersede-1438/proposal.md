# Proposal: openspec-keeper-supersede-1438

Issue: #1438

## Why

A merged PR archives its OpenSpec change, so the archive count moves on `master`.
An already-open `ci/openspec-index-repair-*` keeper cut before that move still
carries its own, lower `archived: **N**` count. It cannot land (the merge-tree
index gate of #1239 reds it), yet the ONE keeper dedupe
(`scripts/keeper_pr.py::keeper_dedupe`) classes it as a LIVE keeper and suppresses
the fresh repair against the current tip. Measured on `master` `ea82354`:
`OPENSPEC.md` says `archived: **486**` while the still-CLEAN keeper PR #1248
(head `03e45f98`) says `archived: **397**` — it lands nothing, blocks a fresh
keeper, and needs manual triage + close (#1425/#1426 hit the same shape on
consecutive days).

## What Changes

- Add a pure `archived_count()` parser and a `classify_superseded()` decision to
  `scripts/keeper_pr.py`: an OPEN, MERGEABLE keeper on the prefix whose head
  `OPENSPEC.md` `archived:` count is BELOW `origin/master`'s is SUPERSEDED.
- `land_keeper` closes every SUPERSEDED keeper with its count evidence BEFORE the
  live/tombstone/unmergeable dedupe, so a stale keeper neither suppresses a fresh
  repair nor lingers DIRTY. A CURRENT keeper keeps suppressing exactly as today.
- Extend `tests/test_keeper_pr.py` with the SUPERSEDED/CURRENT pair and prove the
  guard RED on the pre-change seam.
- Update `ARCHITECTURE.md` (script row + regenerated §10 inventory).

## Impact

No data format, contract, image or workflow wiring change: the dedupe already runs
in the four keeper jobs, and the close uses the token they already carry
(`pull-requests: write`). Nothing is rebased, force-pushed or merged. A keeper at
or above the master count is untouched.

## Not covered

- No change to how a fresh keeper is filed, and no new pipeline or schedule.
- No rulebook change beyond the §8 row this guard owes (declared on #1438).
