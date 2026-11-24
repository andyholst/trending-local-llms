# Proposal: red-first-skill-discipline

Issue: #1497

## Why

The `asimov@mac` fleet wake-up at 2026-11-24 04:35 CET found `make fleet-host-sync-check BASE=origin/master` RED: the live `tll-implementer` lane skill carries a genuinely-new `RED-first` verification discipline clause that is absent from the tracked `agents/tll-implementer/skills/tll-implementer/SKILL.md`. The host divergence is pure addition (three lines, zero deletions) written by an active lane at 03:34:40Z. Wiping it to force the gate green would destroy in-flight work, so it must be landed additively through a reviewed PR.

## What Changes

- Add the `RED-first` clause to the tracked implementer skill as one new numbered step (7), renumbering the existing `Post the result on the issue` step to 8.
- Add `tests/test_red_first_skill.py`, a guard that reads the tracked skill and fails when the clause, the renumbered step, or the single `## This lane` heading is missing.
- Record the finding in `findings.md`.

## Impact

No data format, contract, Makefile target, pipeline job or image changes: this is prose in one agent skill plus one offline guard. `ARCHITECTURE.md` needs no row because no target, stage, job or image is added. The host skill file is left intact with a timestamped backup until this PR lands; the fleet-sync gate goes green only after the merge and the subsequent base re-sync.

## Not covered

- No AGENTS.md / rulebook edit (rule 3c): the change adds a discipline clause to a lane skill, it does not alter a rulebook stage or pipeline contract.
- No host profile file is overwritten, no CI dispatch, no merge, no master push, no collaborator grant.
- The duplicate `## This lane` heading in the host copy is NOT landed; only the genuinely-new clause is.
