# Proposal: rulebook-store-note-pin-order-1612

Issue: #1612
PR: #1600

## Why

Two APPROVED pins contradicted each other on one shared line and reddened PR #1600's
`validate`. `AGENTS.md` §7b's single `Rule 3c note:` line is a SHARED append point: every
lane whose change touches the rulebook appends one clause naming its issue. #1586's approved
landing requires the note to end `#…#1395, #1589, #1586`; #1482's already-merged pin in
`tests/test_agents_store_rows.py` asserted `note.endswith(<its own #1395 clause>)`, i.e.
that `#1395` be LAST. Order A kept #1586's shape and failed that module (CI run
`45411520673`: `177 module(s) passed, 1 FAILED: test_agents_store_rows.py`); Order B moved
`#1395` last and broke #1586's landing. No text satisfies both.

## What Changes

- `tests/test_agents_store_rows.py`: replace the `endswith(CHANGE_2)` assertion with
  PRESENCE + ASCENDING ORDER through one pure predicate,
  `note_carries_clause_after_predecessors(note, clause, predecessors)` — the `#1395`
  clause must occur AND sit after its `#1209`/`#1232`/`#1258` predecessors; later clauses
  (#1589, #1586, …) may follow it. Not weakened to a bare substring check.
- Three new functions registered in the module's own `main()`:
  `test_relaxed_note_accepts_both_landing_orders` (Order A and Order B both pass),
  `test_missing_or_out_of_order_1395_still_reds` (a missing clause and an out-of-order
  clause each fail), and `test_the_brittle_endswith_pin_is_gone_from_this_module`.
- `findings/1612.md`: the per-issue analysis this run owes (rule 6g).

No `AGENTS.md` text changes: Order A stays exactly as landed. No §7b/§8 edit, no SOUL,
no schedule, no new PR — this lands as an amendment to PR #1600's existing branch.

## Impact

One test module plus its analysis file. No schema, contract, API, table, data-shape,
workflow or Makefile change; no dead code; nothing removed. The predicate is pure, so the
RED-first proof runs the real function, not a stand-in. Readers of the rulebook are
unaffected: the note text does not move.

## Not covered

- A mechanical guard over the WHOLE `Rule 3c note` line's clause order. The #1586 findings
  file proposed one ("ascending issue order"), but measured here that wording would red
  #1586's own approved order (`#1589` then `#1586` descend) — recorded as a finding in
  `findings/1612.md`, filed separately.
- Any relaxation of `tests/test_dispatch_guard.py`'s names-only pins (#1586) — they are
  unaffected and stay green.
