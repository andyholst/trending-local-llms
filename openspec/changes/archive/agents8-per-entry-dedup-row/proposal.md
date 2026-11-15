# Proposal: agents8-per-entry-dedup-row

Issue: #1001
PR: #1013

## Why

`data-gap-issue-dedup-per-entry` (#996, merged as `090b735`) landed the per-entry
gap-filing signature and its guard test `test_a_fluctuating_starved_leg_refiles_only_the_new_entry`,
but shipped **no §8 row** — the owed-row ledger (issue #523) tracks exactly this gap and
`make owed-rows-check` reports the row OUTSTANDING. Rule 6c requires a change's guard row in
the §8 table in the same change; when that write was blocked, the owed-row ledger + a pin test
carry it (the #310/#391/#400/#369 model). The §8 table currently describes the OLD whole-SET
signature behaviour while the filer has already moved on — an agent reading the rulebook learns
the wrong contract.

## What Changes

- `AGENTS.md` §8 gains the row #996 owed (tracked as #1001), naming the three landed guards
  (`test_a_fluctuating_starved_leg_refiles_only_the_new_entry`, `test_a_gap_set_is_filed_once`,
  `test_one_issue_per_changed_gap_set`), the measured failure (three identical `context_tokens`
  issues in five hours) and the per-entry contract. The row carries the ledger needle
  `tests/test_data_gap_analysis.py --` verbatim so `make owed-rows-check` can prove it landed.
- `tests/test_agents_rows.py` gains `test_the_per_entry_dedup_row_is_written`, pinning the row
  (rule 6c: the row and its pin ship together).

## Impact

- Protected file: `AGENTS.md` §8 (row addition only — rule 3b additive; rule 3c sign-off is
  this attended run's review, per the owner's standing directive).
- `tests/test_agents_rows.py` (+1 test, wired into `main()` so `make test` runs it).
- Closes the owed-row ledger entry for issue #1001: after this merges, `make owed-rows-check`
  reports `LANDED` with its `AGENTS.md:<line>` evidence and #1001 closes on that proof.

## Not covered

- The per-entry dedup itself — already implemented by #996 (this change lands only the owed
  rulebook row + its pin).
- The §8 row for #1005's `test_the_gap_issue_body_ends_with_a_newline` — that guard has not
  landed on master yet (its PR #1003 is still open); its owed row stays OUTSTANDING until it does.
