# Proposal: fix-loop-self-archive-exit-mapping

Issue: #1582

## Why

`scripts/fix_loop.sh` classifies the outcome of `make self-archive-guard` from the
`make` exit code (`sa_rc`). GNU make rewrites ANY non-zero recipe exit into its own
`2`, while `scripts/self_archive_guard.py` distinguishes `0 clean`, `1 dismantled
(restored when asked)` and `2 unreadable inputs`. The script's `[ "$sa_rc" = "1" ]`
branch therefore can never fire: a round that dismantled its own OpenSpec change and
had it restored is reported as `self-archive guard could not run (exit 2)`, so an
operator reading the repair notes cannot tell a restored self-archive (#812) from an
unreadable baseline.

## What Changes

- `scripts/self_archive_guard.py` prints ONE stable verdict line on stdout —
  `[self-archive] verdict=ok|restored|unrecovered|unreadable` — beside its existing
  prose, so the outcome survives the make exit rewrite. The read-failure path also
  prints `verdict=unreadable` on stdout (the stderr sentence is unchanged).
- `scripts/fix_loop.sh` branches on the verdict marker instead of the rewritten exit
  code: `restored` keeps the issue #812 restoration note, `unrecovered` gets its own
  loud note, and any other non-zero result keeps the `could not run` note.
- `tests/test_self_archive_guard.py` gains guards that drive the REAL guard against a
  planted dismantle and assert the marker contract, plus the fix-loop branch pin.

## Impact

No data format, contract, image, workflow or `make` target change. The #812 protection
is unchanged (a dismantle still stays red); only the operator-facing classification is
corrected. Additive output only — no existing printed line is removed.

## Not covered

- No change to the guard's exit-code contract, the snapshot format or the Makefile
  recipes; the make rewrite is worked around by reading the verdict, not by changing
  either side's exit status.
