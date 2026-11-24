# Proposal: rulebook-fleet-handover-1363

Issue: #1363
PR: #1609

## Why

Rule 3c makes a rulebook change review-required: a guard that lands without its row naming
it has no reviewable home, so a later edit could drop the generated pair from the lane's
conflict list again with nothing naming the loss. Issue #1361 landed the guard
`test_pr_rebase_soul_names_the_generated_artifact_pair` in `tests/test_fleet_handover_protocol.py`
and the matching rule text in `agents/tll-pr-rebase/SOUL.md`, but the existing §8 row for that
module names only three of its behaviours (the status-comment rule, the never-started-run
recovery and the post-delivery duty) and never the fourth. Measured at base `109cc082`:
`test_pr_rebase_soul_names_the_generated_artifact_pair` appears **0** times in `AGENTS.md`,
`#1361` **0**, `#1362` **0**, and the module carries **5** test functions against the row's
three named behaviours.

## What Changes

- `AGENTS.md` §8's EXISTING row for `tests/test_fleet_handover_protocol.py` (line 2496) is
  EXTENDED in place: its Catches cell gains one clause naming the `tll-pr-rebase` lane's
  habitual-conflict entry for the GENERATED pair `OPENSPEC.md` + `ARCHITECTURE.md` §10 with its
  regenerate commands, citing `issue #1361, PR #1362` and the guard name. One line replaced by
  one line; cell 1 byte-identical; the fleet-handover row count stays exactly 1.
- `tests/test_fleet_handover_protocol.py` gains ONE names-only pin,
  `test_section_8_row_names_the_1361_generated_artifact_guard`, registered in the existing
  `main()`. Module total 5 → 6 test functions. No new file, no Makefile change.

No data, contract, workflow, Makefile, script or image change. No §7b bullet and no
`Rule 3c note` clause: #1363 adds no rule, it names an already-ruled lane behaviour.

## Impact

Rulebook prose plus one names-only pin reading the REAL `AGENTS.md` (rule 6m — no fixture).
`scripts/run_tests.sh` globs `tests/test_*.py`, so the module is discovered with no target
change. RED on the base revision (rc=1, exactly 3 needle FAILs), GREEN on the landing head
(rc=0); reverse-RED with the `OPENSPEC.md`/`ARCHITECTURE.md` bullet deleted from
`agents/tll-pr-rebase/SOUL.md` gives rc=1 with exactly 4 generated-pair FAILs — the guard bites
on the guard, not only on the row.

## Not covered

- A §7b bullet or `Rule 3c note` clause for #1363 (ruled out by the reviewer: no rule added).
- The #1482 store-file row, the #1589 push-and-verify row, and the #1586/#1602 rows, which
  have no §8 home yet — disjoint issues.
- Re-syncing the host profile homes from the merged tree.
