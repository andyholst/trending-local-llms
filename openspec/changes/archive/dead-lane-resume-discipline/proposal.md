# Proposal: dead-lane-resume-discipline

Issue: #1501
PR: #1503

## Why

`make fleet-host-sync-check BASE=origin/master` is RED on `tll-planner/skills/tll-planner/SKILL.md`: the live host carries a 9-line, zero-deletion forward note recording that a pushed branch with no PR is a DEAD lane requiring a bounded RESUME, measured on #1467. Wiping it to force the gate green would destroy work an active planner lane wrote.

## What Changes

- Land the DEAD-lane RESUME clause in the tracked `agents/tll-planner/skills/tll-planner/SKILL.md` verbatim, with its three pre-dispatch checks.
- Add `tests/test_dead_lane_resume.py`, which fails when the clause or any of the three checks is missing or when a duplicate section heading appears.
- Record the finding in `findings.md`.

## Impact

No data format, contract, Makefile target, pipeline job or image changes. The host planner skill is left intact with a timestamped backup until this PR lands; the fleet-sync gate goes green only after the merge and the subsequent base re-sync.

## Not covered

- No AGENTS.md / rulebook edit (rule 3c): this lands a discipline note in a lane skill.
- No host file is overwritten, no CI dispatch, no merge, no master push, no collaborator grant.
