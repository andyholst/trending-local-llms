# An owed-row ledger that can prove what already landed

**Issue:** [#523](https://github.com/andyholst/trending-local-llms/issues/523)
**Capability:** `owed-row-ledger`

## Why

Rule 3c makes the AGENTS.md half of a behaviour change review-required, so every
run whose write to `AGENTS.md` was refused filed its own owed-row issue —
#212 #314 #322 #324 #369 #380 #385 #405, each restating the same mechanism and
copying the text to paste. There is no machine-checkable link from an issue to
the §/row it wants, so "already landed" is only knowable by re-reading a thread:
#322's §8 row has existed since #446, #314's sentence was half-present, and the
ledger rots open while a human closes eight issues by hand.

## What Changes

- **A machine-checkable owed-row marker** — one HTML comment per owed row on
  the issue body (`scripts/bot_markers.py` registers the name and shape, per
  rule 6j): it names the target section anchor (rule/§ id), a row key
  (test file / script / make target the row must name), and the exact needle
  text the row must carry. The backlog issues gain their markers through this
  change.
- **`scripts/owed_rows_check.py` + `make owed-rows-check`** — reads the open
  issues carrying the marker (through the ONE queue reader, `scripts/issue_queue.py`
  labels), parses each owed row, and against the tree's `AGENTS.md` reports
  each owed row as `landed` or `outstanding`, with the evidence line. Landed
  rows are reported so the issue can be closed on evidence; a marker the parser
  cannot read is loud, never silent.
- **Wiring** — the check reaches CI through the Makefile (rule 6m) exactly where
  a live GitHub read legally belongs, its tests run offline against recorded
  fixtures (rule 6m: the real script runs, only GitHub is a fixture), and
  `ARCHITECTURE.md` + `AGENTS.md` §8 carry its rows in the same change.

## Impact

- `scripts/owed_rows_check.py` (new), `scripts/bot_markers.py` (marker
  registration), `Makefile` (new target), `AGENTS.md` (§8 row, §6j table row),
  `ARCHITECTURE.md` (generated block + script row), `tests/` (new test module).
- Affected issues: #523 (and the folded #503 rows) gain their marker; issues
  whose rows the check reports as landed become closable on evidence — closing
  them is a human/reviewer act, not this change's.
- **Not covered:** it does not edit any issue body or label (rule 6j: the
  implementer never writes a label or body); it does not close issues; it does
  not re-open the protected-write approval mechanism (#310's shape is unchanged
  — the ledger only records landing state).
