# Proposal: s8-row-r-marker-pr

Issue: #1336
PR: #1338

## Why

`AGENTS.md` §8 is the reviewable claim that a regression test locks an error class. The
`tests/test_watch_monitor.py` row names issues `#1266/#1282/#1312` but **not #1284**, whose
`test_r_marker_carries_its_pull_request` guard landed in `5303fe3` and locks the `:<pr>`
field on an `R:` marker. Rule 6c owes that row in the same change as the guard, so the field
currently has no rulebook home: a reader of §8 cannot find what locks it, and the next agent
can drop the field or the test with no gate naming the loss.

## What Changes

- The §8 row's issue list gains `#1284`.
- The row's description gains the `R:` marker's PR field and the
  `test_r_marker_carries_its_pull_request` guard that locks it, with the RED-on-base proof.

No code, workflow, target, data or contract change.

## Impact

One rulebook row. `tests/test_agents_rows.py` (the table parser and the
rows-name-real-modules check) stays green; the §8 row remains a well-formed table row.

## Not covered

- The other guard modules whose §8 rows may predate their newest guard — each is its own
  finding, and no gate enumerates them.
