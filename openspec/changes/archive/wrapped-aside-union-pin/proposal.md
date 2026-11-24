# Proposal: wrapped-aside-union-pin

Issue: #1605
PR: #1607

## Why

`make fleet-host-sync-check` compares host profile bytes to the tracked mirror, while
`tests/test_fleet_lifecycle.py`'s union pin asserts that no non-trivial line/clause grows past
the pinned union base (`84cace0b`). The pin's aside stripper ran PER LINE, so a parenthetical
aside that OPENS on one line and CLOSES on a later one was never stripped: its inner clause
leaked into the multiset and was counted twice. Measured on #1573's lossless host/mirror union
as exactly `clause 1->2 'gh pr checks'`, which reddened a byte-equal mirror. No tree state
satisfied both gates, so a genuine host-forward note could not land at all.

## What Changes

- `tests/test_fleet_lifecycle.py`: replace the per-line `_PARENTHETICAL` regex with
  `_mask_parentheticals`, a character mask that blanks every BALANCED parenthetical group WHOLE
  — including one that wraps across lines — while preserving newlines so line units and line
  structure survive. `mirror_units`, `_clauses_of` and `_is_duplicate_new_unit` all read the
  masked text through ONE seam, so the scoping key cannot drift from the counter.
- Add a RED-first regression test (`test_a_wrapped_parenthetical_aside_is_stripped_whole`) that
  plants the measured shape — `(empty, ` + `` `gh pr checks` `` on one line and
  `said "no checks reported")` on the next — and fails on the old normaliser, plus teeth that a
  repeated clause OUTSIDE any aside, an exact repeated bullet, the same-line aside and an
  unmatched opener all keep their behaviour.

## Impact

No data, contract, format, target, workflow or host-profile change. The pin's intent is
unchanged: a NEW clause may still not appear past the union base; only the aside handling is
corrected, so the lossless union #1573 needs can finally pass. Only balanced groups are masked;
an unmatched opener is left as written, never allowed to blank the rest of the file.

## Not covered

- No edit to `scripts/fleet_host_sync_check.py`'s byte comparison, no edit to any
  `agents/tll-*` host profile file, and no `AGENTS.md`/§8 rulebook row (this change alters no
  rulebook behaviour). No new make target, pipeline job or schedule.
